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
BOMB_PRODUCTION_COOLDOWN = 5

# Target Scoring Constants
PRODUCTION_MULTIPLIER = 10
BOMB_SCORE_THRESHOLD = 12.3
BOMB_TROOP_THRESHOLD = 50

# Movement Constants
TROOP_OFFENSIVE = 0.53 # Sends this % of troops against superior enemies
TROOP_OFFENSIVE_PRODUCTION_MULTIPLIER = 1.00
TROOP_DEFENSIVE = 1.00 # Sends this % of troops to reinforce friendly targets

# Game Variables
NUM_FACTORIES = 0
INITIAL_FACTORY = -1
INITIAL_FACTORY_ENEMY = -1
FRONTLINE_FACTORY = -1
FRONTLINE_DISTANCE = MAX_INT
CYBORGS_OWN = 0
CYBORGS_ENEMY = 0
num_bombs = 2

# Map Variables
adjList = [] # Adjacency List ordered by shortest distance
adjMatrix = [] # Adjacency Matrix
factoryInfo = [] # Information regarding each factory
troopInfo = [] # Packets for each troop movement
bombInfo = [] # Packets for each bomb movement

# Floyd-Warshall APSP matrix with backtracking
floydWarMatrix = [] # Store shortest distance
floydWarPath = [] # Stores complete path to objective
floydWarNext = [] #TODO: Optimization --> Stores next target?

# Simulation for next n turns
SIMUL_TURNS = 20
simulFac = [] # Simulated Factories for attack options

# Actions
turnMoves = [] # Commands for current turn
turnBombs = [] # Commands to send bombs
turnIncs = [] # Commands to upgrade factories
turnOne = True # Selector for initialization turn events

# Helper Functions
def readMaxAvailTroops(simulStates):
    turn = 0
    ttt = MAX_INT
    availTroops = MAX_INT
    for state in simulStates:
        curTroops = state.troops if (state.owner == 1) else -state.troops
        if (curTroops < availTroops and ((turn < ttt) if availTroops < 0 else True)):
            availTroops = curTroops
            ttt = turn
        turn += 1
    return (availTroops, ttt)

# Decision Making
def scoreTarget(tgtID, curID):
    distanceMultiplier = (1/max(1,(floydWarMatrix[curID][tgtID]**2)))
    score = 0
    score += 7 if factoryInfo[tgtID].troops < factoryInfo[curID].troops else 0
    score += factoryInfo[tgtID].production*PRODUCTION_MULTIPLIER*distanceMultiplier # Rewards production
    score -= max(5, factoryInfo[tgtID].troops*0.5)*distanceMultiplier # Penalizes troops
    print("{0} Score: {1}".format(tgtID, score), file=sys.stderr)
    return score

def scoreBomb(tgtID, curID):
    distanceMultiplier = (1/max(1,(floydWarMatrix[curID][tgtID]**0.5)))
    score = 0
    score += factoryInfo[tgtID].production*PRODUCTION_MULTIPLIER*distanceMultiplier # Rewards production
    score += max(10, factoryInfo[tgtID].troops)*distanceMultiplier # Rewards troops
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

def should_reinforce(facID):
    if (factoryInfo[facID].owner != 1):
        return False
    if (factoryInfo[facID].troops < 1):
        return False
    if (factoryInfo[facID].production < 3):
        return False
    return True

def needed_upgradeTroops(curFac, tgtFac, resolutions):
    ttt = floydWarMatrix[curFac.ID][tgtFac.ID]
    arrivalState = resolutions[tgtFac.ID][ttt]
    if (arrivalState.owner == 1 or arrivalState.owner == 0 or arrivalState.troops == 0):
        if (arrivalState.production < 3):
            requestTroops = FACTORY_UPGRADE_COST - (arrivalState.troops if arrivalState.owner == 1 else -arrivalState.troops)
            if (requestTroops > 0 and requestTroops <= curFac.troops):
                return requestTroops
    return -1

def needed_reinforcements(ttt, availTroops, resolution):
    arrivalState = resolution[ttt]
    # if (arrivalState.owner != 1):
    #     return -1
    # Will be in time to reinforce
    requestTroopsTup = readMaxAvailTroops(resolution) 
    requestTroops = requestTroopsTup[0] # Reads how many troops needed
    requestTurn = requestTroopsTup[1] # Reads when it is needed
    if (requestTroops < 0):
        return max(availTroops, -requestTroops)
    return -1

def viable_upgrade(resolution, prevUpgrades):
    updatedResolutions = []
    # Builds updated states for next FACTORY_UPGRADE_COST turns
    for i in range(max(SIMUL_TURNS, FACTORY_UPGRADE_COST)):
        curState = resolution[i]
        newState = FactoryMsg(curState.ID, [curState.owner, curState.troops, curState.production, curState.cooldown])
        newState.troops = curState.troops - FACTORY_UPGRADE_COST*(prevUpgrades+1) + i*(prevUpgrades+1)
        newState.updateOwnership()
        updatedResolutions.append(newState)
    # Checks for viability given an upgrade
    for state in updatedResolutions:
        if (state.owner != 1):
            return False
    return True

# Classes
class FactoryMsg(object):

    def __init__(self, entityID, args):
        self.ID = entityID
        self.owner = args[0]
        self.troops = args[1]
        self.production = args[2]
        self.cooldown = args[3]

    def updateOwnership(self):
        if (self.troops < 0):
            self.owner *= -1
            self.troops = abs(self.troops)

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
        # Generates array to store simulation
        simulMap = []
        for turn in range(SIMUL_TURNS):
            args = (self.owner, self.troops, self.production, self.cooldown)
            facState = FactoryMsg(self.ID, args)
            simulMap.append(facState)
        # If there's no contention, return current state
        if (len(self.incomming) == 0):
            return simulMap
        self.incomming = sorted(self.incomming, key=lambda x: x.ttt) # Sort by time to target
        
        curCooldown = self.cooldown
        packetIdx = 0
        # Simulates ownership for SIMUL_TURNS turns
        for turn in range(SIMUL_TURNS):
            # Produces Units
            if (turn > 0):
                if (curCooldown <= 0):
                    if (curOwner == 1):
                        curTroops += self.production
                    elif (curOwner == -1):
                        curTroops -= self.production
            # Resolves Battles
            while (packetIdx < len(self.incomming) and self.incomming[packetIdx].ttt <= turn):
                if (self.incomming[packetIdx].owner == 1):
                    curTroops += self.incomming[packetIdx].size
                elif (self.incomming[packetIdx].owner == -1):
                    curTroops -= self.incomming[packetIdx].size
                    if (curTroops <= 0):
                        conquered = True
                packetIdx += 1
            # Explodes bombs
            for bomb in bombInfo:
                if (bomb.owner == 1 and bomb.target == self.ID and bomb.ttt < 1):
                    curTroops -= 0.5*curTroops if abs(0.5*curTroops) > 10 else 10*(-1 if curTroops < 0 else 1)
                    curCooldown = BOMB_PRODUCTION_COOLDOWN
            # Determines factory ownership
            if (curTroops > 0):
                curOwner = 1
            elif (not conquered):
                curOwner = self.owner
            else:
                curOwner = -1
            # Stores current turn simulated result
            simulMap[turn].owner = curOwner
            simulMap[turn].troops = abs(curTroops)
            simulMap[turn].production = self.production
            simulMap[turn].cooldown = curCooldown
            # Decrements cooldown timer
            curCooldown -= 1 if curCooldown > 0 else 0
        if (self.owner == 1):
            print("Resolved Factory {0}:".format(self.ID), file=sys.stderr)
            for i in range(5):
                print("Step {0}: Owner->{1} | Troops->{2} | Production->{3} | Cooldown->{4}".format(i, simulMap[i].owner, simulMap[i].troops, simulMap[i].production, simulMap[i].cooldown), file=sys.stderr)
            print("Max Available Units: {0}".format(readMaxAvailTroops(simulMap)[0]), file=sys.stderr)
            print("Turns before being overrun: {0}".format(readMaxAvailTroops(simulMap)[1]), file=sys.stderr)
        return simulMap # Outputs list of simulated factory state tuples
    
    '''
    Reinforce function
        - Takes a list of targets to be reinforced
        - Weighs targets
        - Sends reinforcements if available
    '''
    def reinforce(self, simulStates):
        curTroops = min(self.troops, readMaxAvailTroops(simulStates[self.ID])[0])
        print("Factory {0} Reinforcing...|Current Troops: {1}".format(self.ID, curTroops), file=sys.stderr)
        if (curTroops < 1):
            return self.actions

        # Get connected friendly reinforcible factories
        adjMyFactories = [facTup[0] for facTup in adjList[self.ID] if (factoryInfo[facTup[0]].owner == 1)]

        # Weighs targets
        weightedTargets = []
        for target in adjMyFactories:
            weightedTargets.append((target, scoreBomb(target, self.ID)))
        weightedTargets = sorted(weightedTargets, key=lambda x: x[1], reverse=True)
        
        # Reinforces targets in weighted order
        for targetTup in weightedTargets:
            target = targetTup[0]
            ttt = floydWarMatrix[self.ID][target]
            requestTroops = needed_reinforcements(ttt, curTroops, simulStates[target])
            if (requestTroops < 0):
                continue
            self.actions.append(MOVE([self.ID, target, requestTroops]))
            curTroops -= requestTroops
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
    def attack(self, simulStates): #TODO: Where to upgrade factories??
        if (self.production == 0 and self.ID != INITIAL_FACTORY):
            self.TROOP_OFFENSIVE = 1
            self.TROOP_DEFENSIVE = 1
        else:
            self.TROOP_OFFENSIVE = TROOP_OFFENSIVE
            self.TROOP_DEFENSIVE = TROOP_DEFENSIVE
        curTroops = min(self.troops, readMaxAvailTroops(simulStates[self.ID])[0])
        print("Factory {0}|Current Troops: {1}".format(self.ID, curTroops), file=sys.stderr)
        if (curTroops < 1):
            self.troops = curTroops
            return self.actions

        validTargets = []
        for adj in adjList[self.ID]:
            ignore = False
            targetFac = factoryInfo[adj[0]]
            targetStates = simulStates[adj[0]]
            ttt = floydWarMatrix[self.ID][targetFac.ID]
            # Filters targets and add some to valid target list
            if (targetStates[ttt].owner == 1):
                ignore = True # Ignore our own factories (no attack necessary)
            else:
                if (targetFac.production == 0):
                    ignore = True # Ignore factories that do not give production
                # We ignore neutral targets with troops that enemies can get to before us
                if (targetFac.owner == 0 and targetFac.troops > self.troops):
                    print("Neutral Factory in contention found...", file=sys.stderr)
                    adjEnemy = -1
                    for adjTup in adjList[targetFac.ID]:
                        if (factoryInfo[adjTup[0]].owner == -1 and factoryInfo[adjTup[0]].troops > 0):
                            adjEnemy = adjTup[0]
                            break
                    print("Closest enemy: {0}".format(adjEnemy), file=sys.stderr)
                    if (adjEnemy != -1 and floydWarMatrix[self.ID][targetFac.ID] >= floydWarMatrix[adjEnemy][targetFac.ID]):
                        ignore = True
            # Ignores blacklisted targets
            if (targetFac.ID in self.blacklist):
                ignore = True
            # Adds valid targets
            if (ignore):
                continue
            else:
                validTargets.append(targetFac)

        # Naive case: no cyborgs!
        for targetFac in validTargets:
            ttt = floydWarMatrix[self.ID][targetFac.ID]
            targetState = simulStates[targetFac.ID][ttt]
            if (targetState.troops == 0 and targetState.owner == 0):
                self.actions.append(MOVE([self.ID, targetFac.ID, 1]))
                curTroops -= 1

        #TODO: Ad-Hoc upgrades (temporary)
        upgradeFactory = True
        curProduction = self.production
        upgrades = 0
        # Decides suitability for upgrading
        while (upgradeFactory):
            # Safety check for troops available
            if (curTroops < FACTORY_UPGRADE_COST):
                upgradeFactory = False
            # Disables upgrades if nearby neutral exists with production
            if (len([fac for fac in validTargets if (fac.owner == 0 and fac.production > 0)]) > 0):
                upgradeFactory = False
            # Checks conditions for an upgrade
            if (curProduction == 3 or not viable_upgrade(simulStates[self.ID], upgrades)):
                upgradeFactory = False
            # Upgrades Current Factory
            if (upgradeFactory):
                upgrades += 1
                curProduction += 1
                print("Upgrading factory with {0} troops at level {1} production".format(curTroops, factoryInfo[self.ID].production), file=sys.stderr)
                self.actions.append(INC([self.ID]))
                curTroops -= FACTORY_UPGRADE_COST
        
        # Weighs targets
        weightedTargets = []
        for targetFac in validTargets:
            weightedTargets.append((targetFac, scoreTarget(targetFac.ID, self.ID)))
        weightedTargets = sorted(weightedTargets, key=lambda x: x[1], reverse=True)
        
        # Attacks targets in weighted order
        for targetTup in weightedTargets:
            if (curTroops < 1):
                self.troops = curTroops
                return self.actions
            targetFac = targetTup[0]
            targetStates = simulStates[targetFac.ID]
            ttt = floydWarMatrix[self.ID][targetFac.ID]
            tttState = targetStates[ttt]
            # Checks that troops won't arrive before bomb :O
            ignore = False
            for bomb in bombInfo:
                if (bomb.owner == 1):
                    print("Bomb from {0}->{1} arrives in: {2} | Attack arrives in: {3}".format(bomb.origin, bomb.target, bomb.ttt, ttt), file=sys.stderr)
                    if (bomb.target == targetFac.ID and ttt <= bomb.ttt):
                        ignore = True
                        break
            # Reserves troops if upgrade can be had in travel time
            # if (self.production < 3 and ttt*self.production >= FACTORY_UPGRADE_COST):
            #     ignore = True
            if (ignore):
                continue
            print("Attacking: {0}".format(targetFac.ID), file=sys.stderr)
            # Determines how many troops to send
            targetAttack = False
            targetTroops = 0
            if (tttState.owner == 0): # Neutral Target
                targetTroops = tttState.troops+1
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
            elif (tttState.owner == -1): # Enemy Target
                # We only attack when our attack can overwhelm enemy
                targetTroops = tttState.troops+3
                if (targetTroops <= curTroops):
                    print("ENEMY! Sending {0} troops".format(targetTroops), file=sys.stderr)
                    targetAttack = True
            # Issues attack command if available
            if (targetAttack):
                self.actions.append(MOVE([self.ID, targetFac.ID, targetTroops]))
                curTroops -= targetTroops
        self.troops = curTroops
        return self.actions

class Strategizer(object):

    def __init__(self, resolutions, simulation, bombs, incs, simulIDCounter):
        self.resolutions = resolutions # 2D list of FactoryMsg objects
        self.actions = []
        self.evalActions = []
        self.upgradeRedistribution = []
        self.blacklistedEnemies = [] # Enemies we can overpower
        self.simulation = simulation
        self.bombs = bombs
        self.incs = incs
        self.simulIDCounter = simulIDCounter

    def simulate(self, actions):
        for move in actions:
            if (move.isMove()):
                if (move.size < 1): # Prunes off no troop packets
                    continue
                args = [1, move.origin, move.target, move.size, adjMatrix[move.origin][move.target]]
                curPacket = TroopMsg(self.simulIDCounter, args)
                self.simulIDCounter += 1
                self.simulation[move.target].pushIncomming(curPacket)

    def prune(self):
        # Prune off excess attacks
        myFactories = [self.simulation[facID] for facID in range(NUM_FACTORIES) if (self.simulation[facID].owner == 1)] # Own factories
        for i in range(len(self.resolutions)):
            simulState = self.resolutions[i]
            if (simulState[-1].owner == 1 and self.simulation[i].owner != 1):
                print("Battle for {0} resolved in our favor, preventing further troops".format(i), file=sys.stderr)
                # Add target to blacklist
                self.blacklistedEnemies.append(i)
        
        # Sends reinforcements
        for fac in myFactories:
            print("Factory {0} reinforcing...".format(fac.ID), file=sys.stderr)
            fac.reinforce(self.resolutions)
        
        # Re-evaluates attack options
        for fac in myFactories:
            print("======================\nFactory {0} attacking...\n======================".format(fac.ID), file=sys.stderr)
            fac.updateBlacklist(self.blacklistedEnemies)
            self.evalActions.extend(fac.attack(self.resolutions))

        #DEBUG: Moves
        for move in self.evalActions:
            print(move.print(), file=sys.stderr)

        # Runs simulation for redirecting
        self.simulate(self.evalActions)

    def upgrade(self):
        myFactories = [self.simulation[facID] for facID in range(NUM_FACTORIES) if should_reinforce(facID)]
        for fac in myFactories:
            curTroops = fac.troops
            for adj in adjList[fac.ID]:
                if (curTroops < 1):
                    break
                adjFac = self.simulation[adj[0]]
                requestTroops = needed_upgradeTroops(fac, adjFac, self.resolutions)
                if (requestTroops > 0):
                    self.upgradeRedistribution.append(MOVE([fac.ID, adjFac.ID, requestTroops]))
                    curTroops -= requestTroops
            fac.troops = curTroops
        # Runs simulation for redirecting
        self.simulate(self.upgradeRedistribution)

    def redirect(self): #TODO: run floyd-warshall per turn?
        for fac in self.simulation:
            for troop in fac.incomming:
                closestIntermediate = floydWarPath[troop.origin][fac.ID][0]
                ttt = floydWarMatrix[troop.origin][closestIntermediate]
                closestIntermediateOwner = self.resolutions[closestIntermediate][ttt].owner
                print("Attempting Redirect:\nTroop destination: {0}\nOrigin: {1}\nIntermediate: {2}".format(fac.ID, troop.origin, closestIntermediate), file=sys.stderr)
                if (closestIntermediate != fac.ID):
                    if (closestIntermediateOwner != 1):
                        continue
                    # Do not route through neutral locations with troops but no production
                    # if (factoryInfo[closestIntermediate].owner == 0 and factoryInfo[closestIntermediate].troops > 0):
                    #     continue
                    # Do not route through enemy teritory
                    # if (factoryInfo[closestIntermediate].owner == -1 and factoryInfo[closestIntermediate].troops > 0):
                    #     continue
                    print("Redirection troop: {0}-->{1} from initial target {2}".format(troop.origin, closestIntermediate, fac.ID), file=sys.stderr)
                    if (fac.delIncomming(troop.ID)):
                        troop.target = closestIntermediate
                        troop.ttt = ttt
                        self.simulation[closestIntermediate].pushIncomming(troop)

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
            factoryInfo[curPacket.target].pushIncomming(curPacket)
            troopInfo.append(curPacket)
            if (curPacket.owner == 1):
                CYBORGS_OWN += curPacket.size
            elif (curPacket.owner == -1):
                CYBORGS_ENEMY += curPacket.size
        elif (entity_type == "BOMB"):
            curPacket = BombMsg(entity_id, args)
            bombInfo.append(curPacket)

    # Resets for frontline factory searching
    if (FRONTLINE_FACTORY != -1 and factoryInfo[FRONTLINE_FACTORY].owner != 1):
        FRONTLINE_DISTANCE = MAX_INT
        FRONTLINE_FACTORY = -1

    # Searches for enemy's initial location
    if (INITIAL_FACTORY == -1 or INITIAL_FACTORY_ENEMY == -1):
        for i in range(len(factoryInfo)):
            if (factoryInfo[i].owner == 1 and INITIAL_FACTORY == -1):
                INITIAL_FACTORY = factoryInfo[i].ID
            if (factoryInfo[i].owner == -1 and INITIAL_FACTORY_ENEMY == -1):
                INITIAL_FACTORY_ENEMY = factoryInfo[i].ID
            if (factoryInfo[i].owner == 1): # Determine a 'frontline' factory
                for adjTup in adjList[i]:
                    if (factoryInfo[adjTup[0]].owner == -1):
                        if (floydWarMatrix[i][adjTup[0]] < FRONTLINE_DISTANCE):
                            FRONTLINE_DISTANCE = floydWarMatrix[i][adjTup[0]]
                            FRONTLINE_FACTORY = i
                            break

    # Launch BOMBS!
    if (num_bombs > 0 and FRONTLINE_FACTORY != -1):
        print("Attempting BOMB", file=sys.stderr)
        # Scores all enemy factores for bombing! :D
        bombTargets = [(fac.ID, scoreBomb(fac.ID, FRONTLINE_FACTORY)) for fac in factoryInfo if (should_bomb(fac.ID))]
        bombTargets = sorted(bombTargets, key=lambda x: x[1], reverse=True)
        for targetTup in bombTargets:
            target = targetTup[0]
            score = targetTup[1]
            if (num_bombs < 1 or len(myFactories) < 1):
                break
            launch = True
            # Only bomb targets above threshold score
            if (score < BOMB_SCORE_THRESHOLD):
                continue
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
    strategize.upgrade() # Takes excess troops to upgrade factories
    strategize.redirect() # Redirects excess troops and paths them via floyd-warshall

    # Output final strategy for the turn
    strategize.print()