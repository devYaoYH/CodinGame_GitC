import sys
import math
from queue import *

# Statics
BOMB_TROOP_THRESHOLD = 50
INITIAL_UPGRADE_DISTANCE_THRESHOLD = 3

# Target Scoring Constants
PRODUCTION_MULTIPLIER = 10

# Attacking Constants
TROOP_OFFENSIVE = 0.2 # Sends this % of troops against superior enemies

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
    print("{0} Score: {1}".format(tgtID, score), file=sys.stderr)
    return score

# Classes
class TroopMsg(object):
    # owner = 0
    # origin = -1
    # target = -1
    # size = -1
    # ttt = -1

    def __init__(self, args):
        self.owner = args[0]
        self.origin = args[1]
        self.target = args[2]
        self.size = args[3]
        self.ttt = args[4]

    def isEnemy(self):
        return (self.owner == -1)

class BombMsg(object):
    # owner = 0
    # origin = -1
    # target = -1
    # ttt = -1

    def __init__(self, args):
        self.owner = args[0]
        self.origin = args[1]
        self.target = args[2]
        self.ttt = args[3]

    def isEnemy(self):
        return (self.owner == -1)

class Action(object):
    # form = ""
    # origin = -1
    # target = -1
    # size = -1

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
    # ID = -1
    # owner = 0
    # troops = 0
    # production = 0
    # cooldown = 0
    # incomming = []
    # outgoing = [] #TODO: not necessary? since outgoing == incomming somewhere else
    # actions = []

    def __init__(self, facID):
        self.ID = facID
        self.owner = 0
        self.troops = 0
        self.production = 0
        self.cooldown = 0
        self.incomming = []
        self.outgoing = []
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
        print("Factory {0} receiving packet...".format(self.ID), file=sys.stderr)
        self.incomming.append((packet.owner, packet.origin, packet.size, packet.ttt))

    def resolve(self): #TODO: Huge function, simulates game till last troop packet arrives
        curTroops = self.troops
        if (len(self.incomming) == 0):
            return (curTroops, 0)
        self.incomming = sorted(self.incomming, key=lambda x: x[3]) # Sort by time to target
        #TODO: Naive implementation --> Computes ownership after all battles resolved
        for packet in self.incomming:
            if (packet[0] == 1):
                curTroops += packet[2]
            elif (packet[0] == -1):
                curTroops -= packet[2]
        return (curTroops, self.incomming[-1][3]) # Outputs tuple (resolution, time to resolution)

    def attack(self): #TODO: Where to upgrade factories??
        curTroops = self.resolve()[0]
        print("Factory {0}|Current Troops: {1}".format(self.ID, curTroops), file=sys.stderr)
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
            print("Scoring valid target: {0}".format(target), file=sys.stderr)
            weightedTargets.append((target, scoreTarget(target, self.ID)))
        weightedTargets = sorted(weightedTargets, key=lambda x: x[1], reverse=True)
        for targetTup in weightedTargets:
            target = targetTup[0]
            print("Acquired valid target: {0}".format(target), file=sys.stderr)
            if (factoryInfo[target].troops+1 < curTroops):
                self.actions.append(MOVE([self.ID, target, factoryInfo[target].troops+1]))
                # print(self.actions[-1].print(), file=sys.stderr)
                curTroops -= (factoryInfo[target].troops+1)
            else:
                self.actions.append(MOVE([self.ID, target, int(TROOP_OFFENSIVE*curTroops)]))
                # print(self.actions[-1].print(), file=sys.stderr)
                curTroops -= int(TROOP_OFFENSIVE*curTroops)
            if (curTroops < 1):
                return self.actions
        return self.actions

class Strategizer(object):
    # resolutions = []
    # actions = []
    # simulation = []
    # bombs = []
    # incs = []

    def __init__(self, resolutions, simulation, bombs, incs):
        self.resolutions = resolutions
        self.actions = []
        self.simulation = simulation
        self.bombs = bombs
        self.incs = incs

    def prune(self):
        return None

    def redirect(self):
        return None

    def upgrade(self):
        return None

    def print(self):
        # Adds movement commands
        for fac in self.simulation:
            print("Simulated Factory {0} has {1} troop packets".format(fac.ID, len(fac.incomming)), file=sys.stderr)
            for troop in fac.incomming:
                self.actions.append(MOVE([troop[1],fac.ID,troop[2]]).print())
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
    factoryInfo.append(Factory(i))
    simulFac.append(Factory(i))
link_count = int(input())  # Number of links between factories
for i in range(link_count): # Initialize adjList/adjMatrix
    factory_1, factory_2, distance = [int(j) for j in input().split()]
    adjList[factory_1].append((factory_2, distance))
    adjList[factory_2].append((factory_1, distance))
    adjMatrix[factory_1][factory_2] = distance
    adjMatrix[factory_2][factory_1] = distance
for i in range(NUM_FACTORIES): # Sort adjList by order of increasing distance
    adjList[i] = sorted(adjList[i], key=lambda x: x[1])
    # print("Factory {0}: {1} connections".format(i, len(adjList[i])), file=sys.stderr)
    # for j in range(len(adjList[i])):
    #     print("Factory {0} --> {1} @ {2}".format(i, adjList[i][j][0], adjList[i][j][1]), file=sys.stderr)

# Game Loop
while True:
    del troopInfo[:] # Resets turn variables
    del bombInfo[:]
    del turnMoves[:]
    del turnBombs[:]
    del turnIncs[:]
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
        elif (entity_type == "TROOP"):
            curPacket = TroopMsg(args)
            factoryInfo[curPacket.target].pushIncomming(curPacket)
            troopInfo.append(curPacket)
        elif (entity_type == "BOMB"):
            curPacket = BombMsg(args)
            bombInfo.append(curPacket)

    # Executes Initial Turn
    if (turnOne):
        #TODO: Does stuffz
        turnOne = False

    # Iterates through all available factories for attack options and stores them in turnMoves
    for i in range(NUM_FACTORIES):
        # print("Factory {0}:\nOwner: {1}\nTroops: {2}\nProduction: {3}".format(factoryInfo[i].ID, factoryInfo[i].owner, factoryInfo[i].troops, factoryInfo[i].production), file=sys.stderr)
        if (factoryInfo[i].owner == 1):
            print("Factory {0} attacking...".format(i), file=sys.stderr)
            turnMoves.extend(factoryInfo[i].attack())

    # Constructs simulated scenario to feed into strategizer
    for move in turnMoves:
        print(move.print(), file=sys.stderr)
        if (move.isMove()):
            args = [1, move.origin, move.target, move.size, adjMatrix[move.origin][move.target]]
            curPacket = TroopMsg(args)
            print("Pushing packet to {0}".format(move.target), file=sys.stderr)
            simulFac[move.target].pushIncomming(curPacket)
        else:
            if (move.form == "BOMB"):
                turnBombs.append(move)
            elif (move.form == "INC"):
                turnIncs.append(move)
                
    for fac in simulFac:
        print("Simulated Factory {0} --> {1} packets".format(fac.ID, len(fac.incomming)), file=sys.stderr)

    # Feed Strategizer
    strategize = Strategizer([fac.resolve() for fac in factoryInfo], simulFac, turnBombs, turnIncs)

    # Strategize!
    strategize.prune() # Conservatively prunes excess troops being sent
    strategize.redirect() # Redirects excess troops
    strategize.upgrade() # Takes excess troops to upgrade factories

    # Output final strategy for the turn
    strategize.print()