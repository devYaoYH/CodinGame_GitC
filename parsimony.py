import sys
import math
from queue import *

# Game Statics
MAX_INT = 65535
FACTORY_UPGRADE_COST = 10

# Upgrade Constants
BOMB_TROOP_THRESHOLD = 50
INITIAL_UPGRADE_DISTANCE_THRESHOLD = 3

# Target Scoring Constants
PRODUCTION_MULTIPLIER = 10

# Attacking Constants
TROOP_OFFENSIVE = 0.47 # Sends this % of troops against superior enemies

# Game Variables
NUM_FACTORIES = 0
INITIAL_FACTORY = -1
INITIAL_FACTORY_ENEMY = -1
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
    score *= (1/(adjMatrix[curID][tgtID]**2))
    # print("{0} Score: {1}".format(tgtID, score), file=sys.stderr)
    return score
        
def should_bomb(facID):
    if (factoryInfo[facID].owner == 1):
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
        self.ID = facID
        self.owner = 0
        self.troops = 0
        self.production = 0
        self.cooldown = 0
        self.incomming = []
        self.outgoing = [] #TODO: not necessary? since outgoing == incomming somewhere else
        self.actions = []

    def tick(self):
        del self.incomming[:]
        del self.outgoing[:]
        del self.actions[:]

    def update(self, args):
        self.owner = args[0]
        self.troops = args[1]
        self.production = args[2]
        self.cooldown = args[3]

    def pushIncomming(self, packet):
        # print("Factory {0} receiving packet...".format(self.ID), file=sys.stderr)
        self.incomming.append(packet)

    def delIncomming(self, packetID):
        idList = [pack.ID for pack in self.incomming]
        if (packetID not in idList): # Error, packet not found
            return False
        else:
            del self.incomming[idList.index(packetID)]
            return True

    def resolve(self): #TODO: Huge function, simulates game till last troop packet arrives
        curTroops = self.troops
        if (len(self.incomming) == 0):
            return (curTroops, 0)
        self.incomming = sorted(self.incomming, key=lambda x: x.ttt) # Sort by time to target
        
        endTime = self.incomming[-1].ttt
        packetIdx = 0
        #TODO: Naive implementation --> Computes ownership after all battles resolved
        for i in range(endTime):
            curTroops += self.production
            while (self.incomming[packetIdx].ttt <= i):
                if (self.incomming[packetIdx].owner == 1):
                    curTroops += self.incomming[packetIdx].size
                elif (self.incomming[packetIdx].owner == -1):
                    curTroops -= self.incomming[packetIdx].size
                packetIdx += 1
        return (curTroops, endTime) # Outputs tuple (resolution, time to resolution)

    def attack(self): #TODO: Where to upgrade factories??
        #curTroops = self.resolve()[0]
        curTroops = self.troops
        print("Factory {0}|Current Troops: {1}".format(self.ID, curTroops), file=sys.stderr)

        # Ad-Hoc upgrades (temporary)
        nearestEnemy = -1
        upgradeFactory = False
        # Finds nearest enemy factory
        for info in adjList[self.ID]:
            if (factoryInfo[info[0]].owner == -1):
                nearestEnemy = info[0]
                break
        # Decides suitability for upgrading
        # print("Distance to nearest enemy: {0}".format(adjMatrix[self.ID][nearestEnemy]), file=sys.stderr)
        if (nearestEnemy == -1):
            upgradeFactory = True
        elif (adjMatrix[self.ID][nearestEnemy] > INITIAL_UPGRADE_DISTANCE_THRESHOLD):
            upgradeFactory = True
        if (curTroops < FACTORY_UPGRADE_COST or self.production == 3):
            upgradeFactory = False
        # Upgrades Current Factory
        if (upgradeFactory):
            print("Upgrading factory with {0} troops at level {1} production".format(curTroops, factoryInfo[self.ID].production), file=sys.stderr)
            self.actions.append(INC([self.ID]))
            curTroops -= FACTORY_UPGRADE_COST

        validTargets = []
        for adj in adjList[self.ID]:
            ignore = False
            if (curTroops < 1):
                return self.actions
            curTarget = adj[0]
            # Filters targets and add some to valid target list
            if (factoryInfo[curTarget].owner == 1):
                ignore = True # Ignore our own factories (no attack necessary)
            else:
                if (factoryInfo[curTarget].production == 0):
                    if (factoryInfo[curTarget].owner == 0):
                        ignore = True # Ignore neutral factories that do not give production
            if (ignore):
                continue
            else:
                validTargets.append(curTarget)
                
        # Naive case: no cyborgs!
        for target in validTargets:
            if (factoryInfo[target].troops == 0):
                self.actions.append(MOVE([self.ID, target, 1]))
                # print(self.actions[-1].print(), file=sys.stderr)
                curTroops -= 1
        
        # Weighs targets
        weightedTargets = []
        for target in validTargets:
            # print("Scoring valid target: {0}".format(target), file=sys.stderr)
            weightedTargets.append((target, scoreTarget(target, self.ID)))
        weightedTargets = sorted(weightedTargets, key=lambda x: x[1], reverse=True)
        for targetTup in weightedTargets:
            target = targetTup[0]
            # print("Acquired valid target: {0}".format(target), file=sys.stderr)
            if (factoryInfo[target].troops+1 < curTroops):
                self.actions.append(MOVE([self.ID, target, factoryInfo[target].troops+1]))
                # print(self.actions[-1].print(), file=sys.stderr)
                curTroops -= (factoryInfo[target].troops+1)
            else:
                if (int(TROOP_OFFENSIVE*curTroops) >= factoryInfo[target].production):
                    self.actions.append(MOVE([self.ID, target, int(TROOP_OFFENSIVE*curTroops)]))
                    # print(self.actions[-1].print(), file=sys.stderr)
                    curTroops -= int(TROOP_OFFENSIVE*curTroops)
            if (curTroops < 1):
                return self.actions
        return self.actions

class Strategizer(object):

    def __init__(self, resolutions, simulation, bombs, incs):
        self.resolutions = resolutions
        self.actions = []
        self.simulation = simulation
        self.bombs = bombs
        self.incs = incs

    def prune(self):
        return None

    def redirect(self):
        for fac in self.simulation:
            for troop in fac.incomming:
                closestIntermediate = floydWarPath[troop.origin][fac.ID][0]
                print("Attempting Redirect:\nTroop destination: {0}\nOrigin: {1}\nIntermediate: {2}".format(fac.ID, troop.origin, closestIntermediate), file=sys.stderr)
                if (closestIntermediate != fac.ID):
                    # Do not route through neutral locations with troops but no production
                    if (factoryInfo[closestIntermediate].owner == 0 and factoryInfo[closestIntermediate].troops > 0):
                        continue
                    # Do not route through enemy teritory
                    if (factoryInfo[closestIntermediate].owner == -1 and factoryInfo[closestIntermediate].troops > 0):
                        continue
                    print("Redirection troop: {0}-->{1} from initial target {2}".format(troop.origin, closestIntermediate, fac.ID), file=sys.stderr)
                    if (fac.delIncomming(troop.ID)):
                        self.simulation[closestIntermediate].pushIncomming(troop)
        return None

    def upgrade(self):
        return None

    def print(self):
        # Adds movement commands
        for fac in self.simulation:
            # print("Simulated Factory {0} has {1} troop packets".format(fac.ID, len(fac.incomming)), file=sys.stderr)
            for troop in fac.incomming:
                self.actions.append(MOVE([troop.origin,fac.ID,troop.size]).print())
        # Adds bomb commands
        for bomb in self.bombs:
            self.actions.append(bomb.print())
        # Adds upgrade commands
        for inc in self.incs:
            self.actions.append(inc.print())
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
    # print("Factory {0}: {1} connections".format(i, len(adjList[i])), file=sys.stderr)
    # for j in range(len(adjList[i])):
    #     print("Factory {0} --> {1} @ {2}".format(i, adjList[i][j][0], adjList[i][j][1]), file=sys.stderr)

# Floyd-Warshall to compute All-Pair Shortest-Paths
for k in range(NUM_FACTORIES):
    for i in range(NUM_FACTORIES):
        for j in range(NUM_FACTORIES):
            if (i==j or k==j):
                continue
            intermediate = floydWarMatrix[i][k] + floydWarMatrix[k][j]
            # print("From {0} to {1}: {2} | With intermediate {3}: {4}".format(i, j, floydWarMatrix[i][j], k, intermediate), file=sys.stderr)
            if (intermediate < floydWarMatrix[i][j]):
                # print("From {0} to {1}: {2} | With intermediate {3}: {4}".format(i, j, floydWarMatrix[i][j], k, intermediate), file=sys.stderr)
                # print(floydWarPath[k][j], file=sys.stderr)
                newPath = [k]
                newPath.extend(floydWarPath[k][j])
                floydWarPath[i][j] = newPath
                # print(floydWarPath[i][j], file=sys.stderr)
                floydWarNext[i][j] = floydWarNext[k][j]
                floydWarMatrix[i][j] = intermediate

# Game Loop
while True:
    del troopInfo[:] # Resets turn variables
    del bombInfo[:]
    del turnMoves[:]
    del turnBombs[:]
    del turnIncs[:]
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
        elif (entity_type == "TROOP"):
            curPacket = TroopMsg(entity_id, args)
            factoryInfo[curPacket.target].pushIncomming(curPacket)
            troopInfo.append(curPacket)
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
    if (turnOne):
        #TODO: Does stuffz
        # Bombs enemy's nearby bases
        bombTargets = []
        if (INITIAL_FACTORY_ENEMY != -1):
            if (factoryInfo[INITIAL_FACTORY_ENEMY].production > 1):
                bombTargets.append(INITIAL_FACTORY_ENEMY)
            for nearby in adjList[INITIAL_FACTORY_ENEMY]:
                if (should_bomb(nearby[0])):
                    bombTargets.append(nearby[0])
        for target in bombTargets:
            if (num_bombs < 1 or len(myFactories) < 1):
                break
            launch = True
            for bomb in bombInfo:
                if (bomb.owner == 1 and bomb.target == target):
                    launch = False
                    break
            if (not launch):
                continue
            turnMoves.append(BOMB([myFactories[0], target]))
            num_bombs -= 1
        if (len(bombTargets) > 0):
            turnOne = False

    # Iterates through all available factories for attack options and stores them in turnMoves
    for i in range(len(myFactories)):
        # print("Factory {0}:\nOwner: {1}\nTroops: {2}\nProduction: {3}".format(factoryInfo[i].ID, factoryInfo[i].owner, factoryInfo[i].troops, factoryInfo[i].production), file=sys.stderr)
        print("Factory {0} attacking...".format(myFactories[i]), file=sys.stderr)
        turnMoves.extend(factoryInfo[myFactories[i]].attack())

    # Constructs simulated scenario to feed into strategizer
    for move in turnMoves:
        print(move.print(), file=sys.stderr)
        if (move.isMove()):
            args = [1, move.origin, move.target, move.size, adjMatrix[move.origin][move.target]]
            curPacket = TroopMsg(simulIDCounter, args)
            simulIDCounter += 1
            # print("Pushing packet to {0}".format(move.target), file=sys.stderr)
            simulFac[move.target].pushIncomming(curPacket)
        else:
            if (move.form == "BOMB"):
                turnBombs.append(move)
            elif (move.form == "INC"):
                turnIncs.append(move)
                
    # for fac in simulFac:
    #     print("Simulated Factory {0} --> {1} packets".format(fac.ID, len(fac.incomming)), file=sys.stderr)

    # Feed Strategizer
    strategize = Strategizer([fac.resolve() for fac in factoryInfo], simulFac, turnBombs, turnIncs)

    # Strategize!
    strategize.prune() # Conservatively prunes excess troops being sent
    strategize.redirect() # Redirects excess troops and paths them via floyd-warshall
    strategize.upgrade() # Takes excess troops to upgrade factories

    # Output final strategy for the turn
    strategize.print()