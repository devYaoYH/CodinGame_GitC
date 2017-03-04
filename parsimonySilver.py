import sys
import math
from queue import *

###################
# Debugging Flags #
###################
MSG_CONTENT = ""
MSG_OUTPUT = False

# Game Statics
MAX_INT = 65535
FACTORY_UPGRADE_COST = 10

# Upgrade Constants
BOMB_TROOP_THRESHOLD = 50
INITIAL_UPGRADE_DISTANCE_THRESHOLD = 3

# Target Scoring Constants
PRODUCTION_MULTIPLIER = 10

# Movement Constants
TROOP_OFFENSIVE = 0.53 # Sends this % of troops against superior enemies
TROOP_OFFENSIVE_PRODUCTION_MULTIPLIER = 0.50
TROOP_DEFENSIVE = 1.00 # Sends this % of troops to reinforce friendly targets

# Game Variables
NUM_FACTORIES = 0
INITIAL_FACTORY = -1
INITIAL_FACTORY_ENEMY = -1
CYBORGS_OWN = 0
CYBORGS_ENEMY = 0
num_bombs = 2

# Map Variables
adjList = [] # Adjacency List ordered by shortest distance
adjMatrix = [] # Adjacency Matrix
factoryInfo = [] # Information regarding each factory
simulFac = [] # Simulated Map for attack options
troopInfo = [] # Packets for each troop movement
bombInfo = [] # Packets for each bomb movement

# Floyd-Warshall APSP matrix with backtracking
floydWarMatrix = [] # Store shortest distance
floydWarPath = [] # Stores complete path to objective
floydWarNext = [] #TODO: Optimization --> Stores next target?

# Actions
turnMoves = [] # Commands for current turn
turnBombs = [] # Commands to send bombs
turnIncs = [] # Commands to upgrade factories
turnOne = True # Selector for initialization turn events

# Helper Functions

# Decision Making
def scoreTarget(tgtID, curID):
    score = 0
    score += factoryInfo[tgtID].production*PRODUCTION_MULTIPLIER
    score *= (1/max(1,(adjMatrix[curID][tgtID]**2)))
    print("{0} Score: {1}".format(tgtID, score), file=sys.stderr)
    return score
        
def should_bomb(facID):
    if (factoryInfo[facID].owner != -1):
        return False
    if (num_bombs < 1):
        return False
    if (factoryInfo[facID].troops > BOMB_TROOP_THRESHOLD):
        return True
    if (factoryInfo[facID].production > 0):
        return True
    return False

# Classes
class TroopMsg(object):

    def __init__(self, entityID, args):
        self.ID = entityID
        self.owner = args[0]
        self.origin = args[1]
        self.target = args[2]
        self.size = args[3]
        self.ttt = args[4]

    def isEnemy(self):
        return (self.owner == -1)

class BombMsg(object):

    def __init__(self, entityID, args):
        self.ID = entityID
        self.owner = args[0]
        self.origin = args[1]
        self.target = args[2]
        self.ttt = args[3]

    def isEnemy(self):
        return (self.owner == -1)

class Action(object):

    def __init__(self, entityType):
        self.form = entityType
        self.origin = -1
        self.target = -1
        self.size = -1

    def isMove(self):
        return (self.form == "MOVE")

class MOVE(Action):

    def __init__(self, args):
        Action.__init__(self, "MOVE")
        self.origin = args[0]
        self.target = args[1]
        self.size = args[2]

    def print(self):
        return "MOVE {0} {1} {2}".format(self.origin, self.target, self.size)

class BOMB(Action):

    def __init__(self, args):
        Action.__init__(self, "BOMB")
        self.origin = args[0]
        self.target = args[1]

    def print(self):
        return "BOMB {0} {1}".format(self.origin, self.target)

class INC(Action):

    def __init__(self, args):
        Action.__init__(self, "INC")
        self.origin = args[0]

    def print(self):
        return "INC {0}".format(self.origin)

class Factory(object):

    def __init__(self, facID):
        global TROOP_OFFENSIVE
        global TROOP_DEFENSIVE
        self.ID = facID
        self.owner = 0
        self.troops = 0
        self.production = 0
        self.cooldown = 0
        self.incomming = []
        self.outgoing = [] #TODO: not necessary? since outgoing == incomming somewhere else
        self.actions = []
        self.blacklist = [] # Blacklisted enemy targets
        self.TROOP_OFFENSIVE = TROOP_OFFENSIVE # Local threshold
        self.TROOP_DEFENSIVE = TROOP_DEFENSIVE # Local threshold

    def tick(self):
        global TROOP_OFFENSIVE
        global TROOP_DEFENSIVE
        global INITIAL_FACTORY
        del self.incomming[:]
        del self.outgoing[:]
        del self.actions[:]
        del self.blacklist[:]

    def update(self, args):
        self.owner = args[0]
        self.troops = args[1]
        self.production = args[2]
        self.cooldown = args[3]

    def updateBlacklist(self, argList):
        self.blacklist = argList

    def pushIncomming(self, packet):
        self.incomming.append(packet)

    def delIncomming(self, packetID):
        idList = [pack.ID for pack in self.incomming]
        if (packetID not in idList): # Error, packet not found
            return False
        else:
            del self.incomming[idList.index(packetID)]
            return True

    def resolve(self): #TODO: Huge function, simulates game till last troop packet arrives
        curTroops = 0
        conquered = False
        curOwner = self.owner
        if (curOwner == 1):
            curTroops = self.troops
        else:
            curTroops = -self.troops
        # If there's no contention, return current state
        if (len(self.incomming) == 0):
            return (curTroops, 0, curTroops)
        self.incomming = sorted(self.incomming, key=lambda x: x.ttt) # Sort by time to target
        
        endTime = self.incomming[-1].ttt
        firstEnemyEncounteredTick = MAX_INT
        availableTroops = curTroops
        packetIdx = 0
        #TODO: Naive implementation --> Computes ownership after all battles resolved
        for i in range(1, endTime+1):
            if (curTroops > 0):
                curOwner = 1
            elif (not conquered):
                curOwner = self.owner
            else:
                curOwner = -1
            # Resolves Battles
            while (packetIdx < len(self.incomming) and self.incomming[packetIdx].ttt <= i):
                if (self.incomming[packetIdx].owner == 1):
                    curTroops += self.incomming[packetIdx].size
                elif (self.incomming[packetIdx].owner == -1):
                    curTroops -= self.incomming[packetIdx].size
                    if (curTroops <= 0):
                        conquered = True
                    # Keeps tabs on available troops (prior to first incomming enemy packet)
                    if (self.incomming[packetIdx].ttt <= firstEnemyEncounteredTick):
                        availableTroops = curTroops
                        firstEnemyEncounteredTick = self.incomming[packetIdx].ttt
                packetIdx += 1
            # Produces Units
            if (curOwner == 1):
                curTroops += self.production
            elif (curOwner == -1):
                curTroops -= self.production
        print("Resolved Factory {0} has {1} troops available".format(self.ID, availableTroops), file=sys.stderr)
        return (curTroops, endTime, availableTroops) # Outputs tuple (resolution, time to resolution, excessTroops)
    
    '''
    Reinforce function
        - Takes a list of targets to be reinforced
        - Weighs targets
        - Sends reinforcements if available
    '''
    def reinforce(self, sosTargets):
        #DEBUG: output state
        MSG_OUTPUT = True
        MSG_CONTENT = "REINFORCING"

        curTroops = self.troops
        print("Factory {0} Reinforcing...|Current Troops: {1}".format(self.ID, curTroops), file=sys.stderr)

        # Weighs targets
        weightedTargets = []
        for targetTup in sosTargets:
            weightedTargets.append((targetTup, scoreTarget(targetTup[0], self.ID)))
        weightedTargets = sorted(weightedTargets, key=lambda x: x[1], reverse=True)
        
        # Reinforces targets in weighted order
        for targetMsg in weightedTargets:
            target = targetMsg[0][0]
            requestTroops = targetMsg[0][1]
            if (requestTroops <= curTroops):
                self.actions.append(MOVE([self.ID, target, requestTroops]))
                curTroops -= (requestTroops)
            else:
                self.actions.append(MOVE([self.ID, target, int(self.TROOP_DEFENSIVE*curTroops)]))
                curTroops -= int(self.TROOP_DEFENSIVE*curTroops)
            if (curTroops < 1):
                self.troops = curTroops
                return self.actions
        self.troops = curTroops
        return self.actions

    '''
    Attack function
        - Prioritizes Upgrade if base will not get overrun in the future
        - Gets a list of valid targets (enemy + neutrals) not in blacklist
        - Weigh valid targets
        - Issues attack commands by priority of weight
    '''
    def attack(self): #TODO: Where to upgrade factories??
        global CYBORGS_OWN
        global CYBORGS_ENEMY
        global TROOP_OFFENSIVE
        global TROOP_DEFENSIVE
        global TROOP_OFFENSIVE_PRODUCTION_MULTIPLIER
        if (self.production == 0 and self.ID != INITIAL_FACTORY):
            self.TROOP_OFFENSIVE = 1
            self.TROOP_DEFENSIVE = 1
        else:
            self.TROOP_OFFENSIVE = TROOP_OFFENSIVE
            self.TROOP_DEFENSIVE = TROOP_DEFENSIVE
        curTroops = self.troops
        print("Factory {0}|Current Troops: {1}".format(self.ID, curTroops), file=sys.stderr)

        validTargets = []
        for adj in adjList[self.ID]:
            ignore = False
            if (curTroops < 1):
                self.troops = curTroops
                return self.actions
            curTarget = adj[0]
            # Filters targets and add some to valid target list
            if (factoryInfo[curTarget].owner == 1):
                ignore = True # Ignore our own factories (no attack necessary)
            else:
                if (factoryInfo[curTarget].production == 0):
                    if (factoryInfo[curTarget].owner == 0):
                        ignore = True # Ignore neutral factories that do not give production
            # Ignores blacklisted targets
            if (curTarget in self.blacklist):
                ignore = True
            # Adds valid targets
            if (ignore):
                continue
            else:
                validTargets.append(curTarget)

        # Naive case: no cyborgs!
        for target in validTargets:
            if (factoryInfo[target].troops == 0 and factoryInfo[target].owner == 0):
                self.actions.append(MOVE([self.ID, target, 1]))
                curTroops -= 1

        #TODO: Ad-Hoc upgrades (temporary)
        nearestEnemy = -1
        upgradeFactory = True
        # Finds nearest enemy factory
        for info in adjList[self.ID]:
            if (factoryInfo[info[0]].owner == -1):
                nearestEnemy = info[0]
                break
        # Decides suitability for upgrading
        # if (nearestEnemy == -1):
        #     upgradeFactory = True
        # elif (adjMatrix[self.ID][nearestEnemy] > INITIAL_UPGRADE_DISTANCE_THRESHOLD):
        #     upgradeFactory = True
        # Prevent upgrade if in Cyborg deficeit
        while (upgradeFactory):
            # if (CYBORGS_OWN - CYBORGS_ENEMY < FACTORY_UPGRADE_COST*0):
            #     upgradeFactory = False
            # Disables upgrades if nearby neutral exists with production
            if (len([facID for facID in validTargets if (factoryInfo[facID].owner == 0 and factoryInfo[facID].production > 0)]) > 0):
                upgradeFactory = False
            # Checks viability for an upgrade
            if (curTroops <= FACTORY_UPGRADE_COST or self.production == 3):
                upgradeFactory = False
            # Upgrades Current Factory
            if (upgradeFactory):
                print("Upgrading factory with {0} troops at level {1} production".format(curTroops, factoryInfo[self.ID].production), file=sys.stderr)
                self.actions.append(INC([self.ID]))
                curTroops -= FACTORY_UPGRADE_COST
                CYBORGS_OWN = CYBORGS_OWN - FACTORY_UPGRADE_COST
        
        # Weighs targets
        weightedTargets = []
        for target in validTargets:
            weightedTargets.append((target, scoreTarget(target, self.ID)))
        weightedTargets = sorted(weightedTargets, key=lambda x: x[1], reverse=True)
        
        # Attacks targets in weighted order
        for targetTup in weightedTargets:
            if (curTroops < 1):
                self.troops = curTroops
                return self.actions
            target = targetTup[0]
            # Checks that troops won't arrive before bomb :O
            ignore = False
            for bomb in bombInfo:
                if (bomb.owner == 1):
                    print("Bomb from {0}->{1} arrives in: {2} | Attack arrives in: {3}".format(bomb.origin, bomb.target, bomb.ttt, floydWarMatrix[self.ID][target]), file=sys.stderr)
                    if (bomb.target == target and floydWarMatrix[self.ID][target] <= bomb.ttt):
                        ignore = True
                        break
            # Reserves troops if upgrade can be had in travel time
            if (self.production < 3 and adjMatrix[self.ID][target]*self.production > FACTORY_UPGRADE_COST):
                ignore = True
            if (ignore):
                continue
            print("Attacking: {0}".format(target), file=sys.stderr)
            # Determines how many troops to send
            targetFac = factoryInfo[target]
            targetAttack = False
            targetTroops = 0
            if (self.production >= 0):
                # Production Factory
                if (targetFac.owner == 0): # Neutral Target
                    targetTroops = targetFac.troops+1
                    if (targetTroops <= curTroops): # Can overwhelm target
                        print("Overwhelming...", file=sys.stderr)
                        targetAttack = True
                    elif (targetTroops <= curTroops+self.production): # Able to target next turn
                        print("Suspend attacks", file=sys.stderr)
                        self.troops = curTroops
                        return self.actions
                    else: # Unable to overwhelm target immediately
                        targetTroops = int(self.TROOP_OFFENSIVE*curTroops)
                        print("Cannot overwhelm, sending {0} troops".format(targetTroops), file=sys.stderr)
                        targetAttack = True
                elif (targetFac.owner == -1): # Enemy Target
                    # We only attack when our attack can overwhelm enemy
                    targetTroops = targetFac.troops+int(TROOP_OFFENSIVE_PRODUCTION_MULTIPLIER*adjMatrix[self.ID][target]*targetFac.production)+1
                    if (targetTroops <= curTroops):
                        print("ENEMY! Sending {0} troops".format(targetTroops), file=sys.stderr)
                        targetAttack = True
            # else:
            #     # Non-production Factory
            #     targetTroops = targetFac.troops+1
            #     if (targetTroops < curTroops): # Can overwhelm target
            #         targetAttack = True
            #     else: # Unable to overwhelm target
            #         targetTroops = int(self.TROOP_OFFENSIVE*curTroops)
            #         if (targetTroops >= targetFac.production):
            #             targetAttack = True
            if (targetAttack):
                self.actions.append(MOVE([self.ID, target, targetTroops]))
                curTroops -= targetTroops
            # else:
            #     if (factoryInfo[target].owner == -1):
            #         if (int(self.TROOP_OFFENSIVE*curTroops) >= factoryInfo[target].production):
            #             self.actions.append(MOVE([self.ID, target, int(self.TROOP_OFFENSIVE*curTroops)]))
            #             curTroops -= int(self.TROOP_OFFENSIVE*curTroops)
            #     else:
            #         self.actions.append(MOVE([self.ID, target, int(self.TROOP_OFFENSIVE*curTroops)]))
            #         curTroops -= int(self.TROOP_OFFENSIVE*curTroops)
        self.troops = curTroops
        return self.actions

class Strategizer(object):

    def __init__(self, resolutions, simulation, bombs, incs, simulIDCounter):
        self.resolutions = resolutions
        self.actions = []
        self.evalActions = []
        self.upgradeRedistribution = []
        self.blacklistedEnemies = [] # Enemies we can overpower
        self.simulation = simulation
        self.bombs = bombs
        self.incs = incs
        self.simulIDCounter = simulIDCounter
        # Modifies available troops in simulation
        ownFactories = [self.simulation[facID] for facID in range(NUM_FACTORIES) if (self.simulation[facID].owner == 1)]
        for fac in ownFactories:
            if (self.resolutions[fac.ID][2] > 0):
                if (fac.troops > self.resolutions[fac.ID][2]):
                    fac.troops = self.resolutions[fac.ID][2]
            else:
                fac.troops = 0

    def simulate(self):
        for move in self.evalActions:
            if (move.isMove()):
                if (move.size < 1):
                    continue
                args = [1, move.origin, move.target, move.size, adjMatrix[move.origin][move.target]]
                curPacket = TroopMsg(self.simulIDCounter, args)
                self.simulIDCounter += 1
                self.simulation[move.target].pushIncomming(curPacket)

    def prune(self):
        # Prune off excess attacks
        sosFactories = [] # Own factories under attack
        reinforcingFactories = [] # Own factories able to reinforce
        for i in range(len(self.resolutions)):
            if (self.resolutions[i][0] > 1):
                if (self.simulation[i].owner != 1):
                    print("Battle for {0} resolved in our favor, preventing further troops".format(i), file=sys.stderr)
                    # Add target to blacklist
                    self.blacklistedEnemies.append(i)
                    # for troop in self.simulation[i].incomming:
                    #     self.simulation[i].delIncomming(troop.ID)
                    #     self.simulation[troop.origin].troops += troop.size
            if (self.resolutions[i][2] <= 0 and self.simulation[i].owner == 1 and self.simulation[i].production > 0):
                sosFactories.append((i, -self.resolutions[i][2]))
            elif (self.simulation[i].owner == 1):
                reinforcingFactories.append(self.simulation[i])
        #DEBUG: Factories under SOS
        for facTup in sosFactories:
            print("SOS! Factory {0} requests {1} troops".format(facTup[0], facTup[1]), file=sys.stderr)
        
        # Sends reinforcements
        for fac in reinforcingFactories:
            print("Factory {0} reinforcing...".format(fac.ID), file=sys.stderr)
            fac.reinforce(sosFactories)
        
        # Re-evaluates attack options
        for fac in reinforcingFactories:
            print("======================\nFactory {0} attacking...\n======================".format(fac.ID), file=sys.stderr)
            fac.updateBlacklist(self.blacklistedEnemies)
            self.evalActions.extend(fac.attack())

        #DEBUG: Moves
        for move in self.evalActions:
            print(move.print(), file=sys.stderr)

        # Runs simulation for redirecting
        self.simulate()

    def redirect(self):
        for fac in self.simulation:
            for troop in fac.incomming:
                closestIntermediate = floydWarPath[troop.origin][fac.ID][0]
                closestIntermediateOwner = 0
                if (self.resolutions[closestIntermediate][0] < 0):
                    closestIntermediateOwner = -1
                else:
                    closestIntermediateOwner = 1
                print("Attempting Redirect:\nTroop destination: {0}\nOrigin: {1}\nIntermediate: {2}".format(fac.ID, troop.origin, closestIntermediate), file=sys.stderr)
                if (closestIntermediate != fac.ID):
                    # Do not route through neutral locations with troops but no production
                    # Do not route through enemy teritory
                    if (closestIntermediateOwner != 1):
                        continue
                    # if (factoryInfo[closestIntermediate].owner == 0 and factoryInfo[closestIntermediate].troops > 0):
                    #     continue
                    # if (factoryInfo[closestIntermediate].owner == -1 and factoryInfo[closestIntermediate].troops > 0):
                    #     continue
                    print("Redirection troop: {0}-->{1} from initial target {2}".format(troop.origin, closestIntermediate, fac.ID), file=sys.stderr)
                    if (fac.delIncomming(troop.ID)):
                        self.simulation[closestIntermediate].pushIncomming(troop)

    def upgrade(self):
        myFactories = [self.simulation[facID] for facID in range(NUM_FACTORIES) if (self.simulation[facID].owner == 1 and self.resolutions[facID][0] > 0 and self.simulation[facID].troops > 0 and self.simulation[facID].production == 3)]
        for fac in myFactories:
            curTroops = fac.troops
            for adj in adjList[fac.ID]:
                if (curTroops < 1):
                    break
                if (adj in self.blacklistedEnemies): # Skips already 'conqured' factories
                    continue
                adjFac = self.simulation[adj[0]]
                if (adjFac.owner == 1 and adjFac.production < 3):
                    # Send it some troops
                    requestTroops = FACTORY_UPGRADE_COST - adjFac.production*adjMatrix[fac.ID][adjFac.ID]
                    if (requestTroops > 0 and requestTroops <= curTroops):
                        self.upgradeRedistribution.append(MOVE([fac.ID, adjFac.ID, requestTroops]))
                        curTroops -= requestTroops
                elif (adjFac.owner == 0):
                    # Send it some troops
                    requestTroops = FACTORY_UPGRADE_COST + adjFac.troops
                    if (requestTroops > 0 and requestTroops <= curTroops):
                        self.upgradeRedistribution.append(MOVE([fac.ID, adjFac.ID, requestTroops]))
                        curTroops -= requestTroops
            fac.troops = curTroops

    def print(self):
        # Adds movement commands
        for fac in self.simulation:
            for troop in fac.incomming:
                self.actions.append(MOVE([troop.origin,fac.ID,troop.size]).print())
        # Adds bomb commands
        for bomb in self.bombs:
            self.actions.append(bomb.print())
        # Adds upgrade commands
        for action in self.evalActions:
            if (action.form == "INC"):
                self.actions.append(action.print())
        for inc in self.incs:
            self.actions.append(inc.print())
        # Adds upgrade redistribution commands
        for move in self.upgradeRedistribution:
            self.actions.append(move.print())
        # Adds in debuggin message
        if (MSG_OUTPUT):
            self.actions.append("MSG {0}".format(MSG_CONTENT))
        # Outputs current turn's actions
        if (len(self.actions) < 1):
            print("WAIT")
        else:
            outputCommand = ""
            for cmd in self.actions:
                outputCommand += ";"
                outputCommand += cmd
            print(outputCommand[1:])

# Handle Inputs
NUM_FACTORIES = int(input())  # Number of factories
for i in range(NUM_FACTORIES): # Initialize Factories
    adjList.append([])
    adjMatrix.append([0 for x in range(NUM_FACTORIES)])
    floydWarMatrix.append([MAX_INT for x in range(NUM_FACTORIES)]) # Matrix to store shortest distances
    floydWarPath.append([[-1] for x in range(NUM_FACTORIES)]) # Matrix to store path
    floydWarNext.append([-1 for x in range(NUM_FACTORIES)]) # Optimized matrix storing only next target
    factoryInfo.append(Factory(i))
    simulFac.append(Factory(i))
link_count = int(input())  # Number of links between factories
for i in range(link_count): # Initialize adjList/adjMatrix
    factory_1, factory_2, distance = [int(j) for j in input().split()]
    adjList[factory_1].append((factory_2, distance))
    adjList[factory_2].append((factory_1, distance))
    adjMatrix[factory_1][factory_2] = distance
    adjMatrix[factory_2][factory_1] = distance
    # Stores links into floyd-warshall graph
    floydWarMatrix[factory_1][factory_2] = distance
    floydWarMatrix[factory_2][factory_1] = distance
    floydWarPath[factory_1][factory_2] = [factory_2]
    floydWarPath[factory_2][factory_1] = [factory_1]
    floydWarNext[factory_1][factory_2] = factory_2
    floydWarNext[factory_2][factory_1] = factory_1
for i in range(NUM_FACTORIES): # Sort adjList by order of increasing distance
    adjList[i] = sorted(adjList[i], key=lambda x: x[1])

# Floyd-Warshall to compute All-Pair Shortest-Paths
for k in range(NUM_FACTORIES):
    for i in range(NUM_FACTORIES):
        for j in range(NUM_FACTORIES):
            if (i==j or k==j):
                continue
            intermediate = floydWarMatrix[i][k] + floydWarMatrix[k][j]
            if (intermediate < floydWarMatrix[i][j]):
                newPath = [k]
                newPath.extend(floydWarPath[k][j])
                floydWarPath[i][j] = newPath
                floydWarNext[i][j] = floydWarNext[k][j]
                floydWarMatrix[i][j] = intermediate

# Game Loop
while True:
    MSG_OUTPUT = False
    del troopInfo[:] # Resets turn variables
    del bombInfo[:]
    del turnMoves[:]
    del turnBombs[:]
    del turnIncs[:]
    CYBORGS_OWN = 0
    CYBORGS_ENEMY = 0
    myFactories = []
    simulIDCounter = 0
    for i in range(NUM_FACTORIES): # Ticks each factory
        factoryInfo[i].tick()
        simulFac[i].tick()

    # Reads game turn state
    entity_count = int(input())  # the number of entities (e.g. factories and troops)
    for i in range(entity_count):
        entity_id, entity_type, arg_1, arg_2, arg_3, arg_4, arg_5 = input().split()
        entity_id = int(entity_id)
        args = [int(arg_1), int(arg_2), int(arg_3), int(arg_4), int(arg_5)]
        if (entity_type == "FACTORY"):
            factoryInfo[entity_id].update(args)
            simulFac[entity_id].update(args)
            if (factoryInfo[entity_id].owner == 1):
                myFactories.append(entity_id)
                CYBORGS_OWN += factoryInfo[entity_id].troops
            elif (factoryInfo[entity_id].owner == -1):
                CYBORGS_ENEMY += factoryInfo[entity_id].troops
        elif (entity_type == "TROOP"):
            curPacket = TroopMsg(entity_id, args)
            # print("Pushing package {0} troops {1}->{2}".format(curPacket.size, curPacket.origin, curPacket.target), file=sys.stderr)
            factoryInfo[curPacket.target].pushIncomming(curPacket)
            troopInfo.append(curPacket)
            if (curPacket.owner == 1):
                CYBORGS_OWN += curPacket.size
            elif (curPacket.owner == -1):
                CYBORGS_ENEMY += curPacket.size
        elif (entity_type == "BOMB"):
            curPacket = BombMsg(entity_id, args)
            bombInfo.append(curPacket)

    # Searches for enemy's initial location
    if (INITIAL_FACTORY == -1 or INITIAL_FACTORY_ENEMY == -1):
        for i in range(len(factoryInfo)):
            if (factoryInfo[i].owner == 1 and INITIAL_FACTORY == -1):
                INITIAL_FACTORY = factoryInfo[i].ID
            if (factoryInfo[i].owner == -1 and INITIAL_FACTORY_ENEMY == -1):
                INITIAL_FACTORY_ENEMY = factoryInfo[i].ID

    # Executes Initial Turn
    # if (turnOne):
    #     #TODO: Does stuffz
    #     # Bombs enemy's nearby bases
    #     bombTargets = []
    #     if (INITIAL_FACTORY_ENEMY != -1):
    #         if (factoryInfo[INITIAL_FACTORY_ENEMY].production > 1):
    #             bombTargets.append(INITIAL_FACTORY_ENEMY)
    #         for nearby in adjList[INITIAL_FACTORY_ENEMY]:
    #             if (should_bomb(nearby[0])):
    #                 bombTargets.append(nearby[0])
    #     for target in bombTargets:
    #         if (num_bombs < 1 or len(myFactories) < 1):
    #             break
    #         launch = True
    #         # Do not bomb same target twice
    #         for bomb in bombInfo:
    #             if (bomb.owner == 1 and bomb.target == target):
    #                 launch = False
    #                 break
    #         # Do not bomb targets that you'll capture first
    #         if (floydWarMatrix[INITIAL_FACTORY][target] < floydWarMatrix[INITIAL_FACTORY_ENEMY][target] and INITIAL_FACTORY_ENEMY != target):
    #             launch = False
    #         if (not launch):
    #             continue
    #         # Find the closest base to launch bomb from
    #         nearestFactory = myFactories[0]
    #         for adjTup in adjList[target]:
    #             if (adjTup[0] in myFactories):
    #                 nearestFactory = adjTup[0]
    #                 break
    #         turnMoves.append(BOMB([nearestFactory, target]))
    #         num_bombs -= 1
    #     if (len(bombTargets) > 0):
    #         turnOne = False

    # Launch BOMBS!
    if (num_bombs > 0 and INITIAL_FACTORY != -1):
        print("Attempting BOMB", file=sys.stderr)
        # Scores all enemy factores for bombing! :D
        bombTargets = [(fac.ID, scoreTarget(fac.ID, INITIAL_FACTORY)) for fac in factoryInfo if (should_bomb(fac.ID))]
        bombTargets = sorted(bombTargets, key=lambda x: x[1], reverse=True)
        for targetTup in bombTargets:
            target = targetTup[0]
            if (num_bombs < 1 or len(myFactories) < 1):
                break
            launch = True
            # Do not bomb same target twice
            for bomb in bombInfo:
                if (bomb.owner == 1 and bomb.target == target):
                    launch = False
                    break
            if (not launch):
                continue
            # Find the closest base to launch bomb from
            nearestFactory = myFactories[0]
            for adjTup in adjList[target]:
                if (adjTup[0] in myFactories):
                    nearestFactory = adjTup[0]
                    break
            turnMoves.append(BOMB([nearestFactory, target]))
            num_bombs -= 1


    # Iterates through all available factories for attack options and stores them in turnMoves
    # for i in range(len(myFactories)):
    #     MSG_OUTPUT = True
    #     MSG_CONTENT = "ATTACKING..."
    #     print("Factory {0} attacking...".format(myFactories[i]), file=sys.stderr)
    #     turnMoves.extend(factoryInfo[myFactories[i]].attack())

    # Constructs simulated scenario to feed into strategizer
    for move in turnMoves:
        print(move.print(), file=sys.stderr)
        if (move.isMove()):
            args = [1, move.origin, move.target, move.size, adjMatrix[move.origin][move.target]]
            curPacket = TroopMsg(simulIDCounter, args)
            simulIDCounter += 1
            simulFac[move.target].pushIncomming(curPacket)
        else:
            if (move.form == "BOMB"):
                turnBombs.append(move)
            elif (move.form == "INC"):
                turnIncs.append(move)

    # Feed Strategizer
    strategize = Strategizer([fac.resolve() for fac in factoryInfo], simulFac, turnBombs, turnIncs, simulIDCounter)

    # Strategize!
    strategize.prune() # Conservatively prunes excess troops being sent
    strategize.redirect() # Redirects excess troops and paths them via floyd-warshall
    strategize.upgrade() # Takes excess troops to upgrade factories

    # Output final strategy for the turn
    strategize.print()