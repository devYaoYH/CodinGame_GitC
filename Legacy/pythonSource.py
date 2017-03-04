import sys
import math
from queue import *

# Auto-generated code below aims at helping you parse
# the standard input according to the problem statement.

BOMB_TROOP_THRESHOLD = 50
INITIAL_UPGRADE_DISTANCE_THRESHOLD = 3
INITIAL_FACTORY = -1
INITIAL_FACTORY_ENEMY = -1

num_bombs = 2
adjList = []
adjMatrix = []
factoryInfo = []
troopInfo = []
bombInfo = []
turnMoves = []
turnOne = True

# Handle Inputs
factory_count = int(input())  # the number of factories
for i in range(factory_count):
    adjList.append([])
    adjMatrix.append([0 for x in range(factory_count)])
    factoryInfo.append([0,0,0,0])
link_count = int(input())  # the number of links between factories
for i in range(link_count):
    factory_1, factory_2, distance = [int(j) for j in input().split()]
    adjList[factory_1].append((factory_2, distance))
    adjList[factory_2].append((factory_1, distance))
    adjMatrix[factory_1][factory_2] = distance
    adjMatrix[factory_2][factory_1] = distance
for i in range(factory_count):
    adjList[i] = sorted(adjList[i], key=lambda x: x[1])
    print("Factory {0}: {1} connections".format(i, len(adjList[i])), file=sys.stderr)
    for j in range(len(adjList[i])):
        print("Factory {0} --> {1} @ {2}".format(i, adjList[i][j][0], adjList[i][j][1]), file=sys.stderr)

# Functions
def factoryCombat(facID):
    print("Factory {0} attacking...".format(facID), file=sys.stderr)
    curFactoryTroops = factoryInfo[facID][1]
    targetFactory = []
    validTarget = []
    nearestEnemy = -1
    upgradeFactory = False
    upgradeCommand = ""
    factoryUpgraded = False
    
    # Finds nearest enemy factory
    for info in adjList[facID]:
        if (factoryInfo[info[0]][0] == -1):
            nearestEnemy = info[0]
            break
    # Decides suitability for upgrading
    print("Distance to nearest enemy: {0}".format(adjMatrix[facID][nearestEnemy]), file=sys.stderr)
    if (nearestEnemy == -1):
        upgradeFactory = True
    elif (adjMatrix[facID][nearestEnemy] > INITIAL_UPGRADE_DISTANCE_THRESHOLD or factoryInfo[nearestEnemy][1] < curFactoryTroops):
        upgradeFactory = True
    # Upgrades Current Factory
    if (upgradeFactory):
        print("Upgrading factory with {0} troops at level {1} production".format(curFactoryTroops, factoryInfo[facID][2]), file=sys.stderr)
        if (curFactoryTroops > 10 and factoryInfo[facID][2] < 3):
            upgradeCommand = "INC {0}".format(facID)
            curFactoryTroops -= 10
            factoryUpgraded = True
            
    for j in range(len(adjList[facID])):
        if (curFactoryTroops < 2):
            break
        curTarget = adjList[facID][j][0]
        if (factoryInfo[curTarget][0] == 1 or factoryInfo[curTarget][2] == 0):
            continue
        else:
            if (factoryInfo[curTarget][0] != 0):
                validTarget.append(curTarget)
        print("Non-friendly Neighbour: {0}".format(curTarget), file=sys.stderr)
        if (factoryInfo[curTarget][1] == 0):
            targetFactory.append((curTarget,1))
            curFactoryTroops -= 1
        elif (factoryInfo[curTarget][1] < curFactoryTroops-1):
            targetFactory.append((curTarget,factoryInfo[curTarget][1]+1))
            curFactoryTroops -= (factoryInfo[curTarget][1]+1)
    if (len(targetFactory) == 0):
        for target in validTarget:
            targetFactory.append((target,int(0.1*curFactoryTroops)))
            curFactoryTroops -= int(0.1*curFactoryTroops)
    if (len(targetFactory) == 0):
        if (factoryUpgraded):
            return upgradeCommand
        else:
            return None
    else:
        factoryCommand = ""
        for cmd in targetFactory:
            factoryCommand = factoryCommand + ";" + "MOVE {0} {1} {2}".format(facID, cmd[0], cmd[1])
        factoryCommand = factoryCommand[1:]
        if (factoryUpgraded):
            factoryCommand = factoryCommand + ";" + upgradeCommand
        return factoryCommand

def valid(facID):
    for i in range(len(adjList[facID])):
        curFac = adjList[facID][i][0]
        if (factoryInfo[curFac][0]==0):
            return True
        elif (factoryInfo[curFac][0]==-1):
            return True
    return False

def bfsBorderFactory(initFacID):
    if (valid(initFacID)):
        return initFacID
    q = Queue()
    visited = []
    for i in range(len(adjList[initFacID])):
        curFac = adjList[initFacID][i][0]
        if (factoryInfo[curFac][0] == 1):
            q.put(curFac)
    visited.append(initFacID)
    while(not q.empty()):
        cur = q.get()
        if (valid(cur)):
            return cur
        if (cur in visited):
            continue
        for i in range(len(adjList[cur])):
            curFac = adjList[cur][i][0]
            if (factoryInfo[curFac][0] == 1):
                q.put(curFac)
        visited.append(cur)
        
def should_bomb(facID, troops, production):
    if (factoryInfo[facID][0] == 1):
        return False
    if (num_bombs < 1):
        return False
    if (troops > BOMB_TROOP_THRESHOLD):
        return True
    if (production > 0):
        return True
    return False

# game loop
while True:
    del troopInfo[:]
    del bombInfo[:]
    del turnMoves[:]
    moved = False
    bombLaunched = False
    bombTargets = []
    launchBomb = False
    bombTarget = -1
    
    # Reads game turn state
    entity_count = int(input())  # the number of entities (e.g. factories and troops)
    for i in range(entity_count):
        entity_id, entity_type, arg_1, arg_2, arg_3, arg_4, arg_5 = input().split()
        entity_id = int(entity_id)
        arg_1 = int(arg_1)
        arg_2 = int(arg_2)
        arg_3 = int(arg_3)
        arg_4 = int(arg_4)
        arg_5 = int(arg_5)
        if (entity_type == "FACTORY"):
            factoryInfo[entity_id][0] = arg_1
            factoryInfo[entity_id][1] = arg_2
            factoryInfo[entity_id][2] = arg_3
            factoryInfo[entity_id][3] = entity_id
        elif (entity_type == "TROOP"):
            troopInfo.append([int(arg_1), int(arg_2), int(arg_3), int(arg_4), int(arg_5)])
        elif (entity_type == "BOMB"):
            print("Halp, there's a BOMB!!", file=sys.stderr)
            bombInfo.append([int(arg_1), int(arg_2), int(arg_3), int(arg_4)])
    
    # Debug Factory Info
    for i in range(len(factoryInfo)):
        if (factoryInfo[i][0] == 1 and INITIAL_FACTORY == -1):
            INITIAL_FACTORY = factoryInfo[i][3]
        if (factoryInfo[i][0] == -1 and INITIAL_FACTORY_ENEMY == -1):
            INITIAL_FACTORY_ENEMY = factoryInfo[i][3]
        print("Factory {0} --> Owned by: {1} | Troops: {2} | Production: {3} | ID: {4}".format(i, factoryInfo[i][0], factoryInfo[i][1], factoryInfo[i][2], factoryInfo[i][3]), file=sys.stderr)
    
    myFactories = []
    for i in range(len(factoryInfo)):
        if (factoryInfo[i][0]==1):
            myFactories.append(factoryInfo[i])
    print("My Factories: {0}".format(len(myFactories)), file=sys.stderr)
    myFactories = sorted(myFactories, key=lambda x: x[1], reverse=True)

    # Do Turn 1 stuff
    if (turnOne):
        if (INITIAL_FACTORY_ENEMY != -1):
            if (factoryInfo[INITIAL_FACTORY_ENEMY][2] > 1):
                bombTargets.append(INITIAL_FACTORY_ENEMY)
            for nearby in adjList[INITIAL_FACTORY_ENEMY]:
                if (should_bomb(nearby[0], factoryInfo[nearby[0]][1], factoryInfo[nearby[0]][2])):
                    bombTargets.append(nearby[0])
        for target in bombTargets:
            if (num_bombs < 1 or len(myFactories) < 1):
                break
            launch = True
            for bomb in bombInfo:
                print("Bomb {0} from {1} --> {2}".format(bomb[0], bomb[1], bomb[2]), file=sys.stderr)
                if (bomb[0] == 1 and bomb[2] == target):
                    launch = False
                    break
            if (not launch):
                continue
            turnMoves.append("BOMB {0} {1}".format(myFactories[0][3], target))
            num_bombs -= 1
        if (len(bombTargets) > 0):
            turnOne = False
    
    # Determine which factory to combat
    if (len(myFactories) > 0):
        actionFactory = bfsBorderFactory(myFactories[0][3])
    print("Action Factory: {0}".format(actionFactory), file=sys.stderr)

    # All Factories Attack
    for i in range(len(myFactories)):
        turnMoves.append(factoryCombat(myFactories[i][3]))
        
    # Check for bomb targets
    # if (not bombLaunched and len(myFactories) > 0):
    #     for fac in factoryInfo:
    #         if (should_bomb(fac[3], fac[1], fac[2])):
    #             launchBomb = True
    #             bombTarget = fac[3]
    #     for bomb in bombInfo:
    #         print("Bomb {0} from {1} --> {2}".format(bomb[0], bomb[1], bomb[2]), file=sys.stderr)
    #         if (bomb[0] == 1 and bomb[2] == bombTarget):
    #             launchBomb = False
    #     if (launchBomb and bombTarget != -1):
    #         turnMoves.append("BOMB {0} {1}".format(myFactories[len(myFactories)-1][3], bombTarget))
    #         num_bombs -= 1

    # Concatenates all commands before executing
    turnCommand = ""
    for turn in turnMoves:
        if (turn != None):
            turnCommand = turnCommand + ";" + turn
    turnCommand = turnCommand[1:]
    if (turnCommand == ""):
        print("WAIT")
    else:
        print(turnCommand)