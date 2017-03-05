    '''
    Reinforce function
        - Takes a list of targets to be reinforced
        - Weighs targets
        - Sends reinforcements if available
    '''
    def reinforce(self, simulStates): #TODO: How to bring troops to the front?
        curTroops = min(self.troops, readMaxAvailTroops(simulStates[self.ID])[0])
        print >> sys.stderr, "Factory {0} Reinforcing...|Current Troops: {1}".format(self.ID, curTroops)
        if (curTroops < 1):
            return self.actions

        # Get connected friendly reinforcible factories
        adjMyFactories = [facTup[0] for facTup in adjList[self.ID] if (factoryInfo[facTup[0]].owner == 1)]

        # Weighs targets
        weightedTargets = []
        for target in adjMyFactories:
            weightedTargets.append((target, scoreRedistribution(target, self.ID, factoryInfo[target].closestEnemy()[1])))
        weightedTargets = sorted(weightedTargets, key=lambda x: x[1], reverse=True)
        
        # Reinforces targets in weighted order
        for targetTup in weightedTargets:
            if (curTroops < 1):
                self.troops = curTroops
                return self.actions
            target = targetTup[0]
            ttt = floydWarMatrix[self.ID][target]+1
            print >> sys.stderr, "Reinforcing factory {0}:".format(target)
            requestTroops = needed_reinforcements(ttt, curTroops, simulStates[target])
            if (requestTroops < 0):
                continue
            self.actions.append(MOVE([self.ID, target, requestTroops]))
            print >> sys.stderr, self.actions[-1].printCmd()
            curTroops -= requestTroops

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
        print >> sys.stderr, "Factory {0}|Current Troops: {1}".format(self.ID, curTroops)
        if (curTroops < 1):
            self.troops = curTroops
            return self.actions

        validTargets = []
        for adj in adjList[self.ID]:
            ignore = False
            targetFac = factoryInfo[adj[0]]
            targetStates = simulStates[adj[0]]
            ttt = floydWarMatrix[self.ID][targetFac.ID]+1
            
            # print("Evaluating target Factory: {0}".format(adj[0]), file=sys.stderr)
            # Filters targets and add some to valid target list
            if (targetStates[ttt].owner == 1):
                # print("IGNORE -> Owned", file=sys.stderr)
                ignore = True # Ignore our own factories (no attack necessary)
            else:
                if (targetFac.production == 0):
                    # print("IGNORE -> Production 0", file=sys.stderr)
                    ignore = True # Ignore factories that do not give production
            
            # Ignores blacklisted targets
            if (targetFac.ID in self.blacklist):
                # print("IGNORE -> Blacklisted", file=sys.stderr)
                ignore = True
            
            # Adds valid targets
            if (ignore):
                continue
            else:
                # print("VALID! :)", file=sys.stderr)
                validTargets.append(targetFac)

        # Naive case: no cyborgs!
        for targetFac in validTargets:
            if (curTroops < 1):
                self.troops = curTroops
                return self.actions
            ttt = floydWarMatrix[self.ID][targetFac.ID]+1
            targetState = simulStates[targetFac.ID][ttt]
            if (targetState.troops == 0 and targetState.owner == 0):
                self.actions.append(MOVE([self.ID, targetFac.ID, 1]))
                print >> sys.stderr, self.actions[-1].printCmd()
                curTroops -= 1
                targetFac = None #TODO: Removes target from list?
        validTargets = [fac for fac in validTargets if fac != None] # Removes None-types

        #TODO: Ad-Hoc upgrades (temporary)
        upgradeFactory = True
        curProduction = self.production
        upgrades = 0
        #EXPERIMENTAL: Don't too aggressively upgrade factories close to the enemy
        adjFriendlyTup = self.closestFriendly()
        adjEnemyTup = self.closestEnemy()
        if (adjFriendlyTup[0] == -1): # Initial Factory or only factory
            if (adjEnemyTup[0] != -1):
                if (adjEnemyTup[1] < MAP_RUSH_SIZE):
                    upgradeFactory = False
        if (adjFriendlyTup[0] != -1 and adjEnemyTup[0] != -1):
            # print("Testing viability for upgrade based on distance to enemy", file=sys.stderr)
            # print("Distance to friendly factory {0}: {1} | Distance to enemy factory {2}: {3}".format(adjFriendlyTup[0], adjFriendlyTup[1], adjEnemyTup[0], adjEnemyTup[1]), file=sys.stderr)
            if (adjEnemyTup[1] <= adjFriendlyTup[1] and (CYBORGS_OWN - CYBORGS_ENEMY) < FACTORY_UPGRADE_COST):
                upgradeFactory = False
        # Decides suitability for upgrading
        while (upgradeFactory):
            # Safety check for troops available
            if (curTroops < FACTORY_UPGRADE_COST):
                upgradeFactory = False
            # Disables upgrades if nearby neutral exists with production
                # On the condition that one can take it
                # And such a move would bring about more overall units than upgrading
            neutralFactories = []
            for targetFac in validTargets:
                targetStates = simulStates[targetFac.ID]
                ttt = floydWarMatrix[self.ID][targetFac.ID]+1
                tttState = targetStates[ttt]
                if (tttState.owner == 0 and tttState.production > 0):
                    tttDiff = FACTORY_UPGRADE_COST - ttt
                    if (tttDiff < 0 or tttState.production*tttDiff > FACTORY_UPGRADE_COST and tttState.troops < curTroops):
                        neutralFactories.append(targetFac.ID)
            if (len(neutralFactories) > 0):
                upgradeFactory = False
            # Checks conditions for an upgrade
            if (curProduction == 3 or not self.viable_upgrade(simulStates[self.ID], upgrades)):
                upgradeFactory = False
            # Upgrades Current Factory
            if (upgradeFactory):
                upgrades += 1
                curProduction += 1
                print >> sys.stderr, "Upgrading factory with {0} troops at level {1} production".format(curTroops, factoryInfo[self.ID].production)
                self.actions.append(INC([self.ID]))
                curTroops -= FACTORY_UPGRADE_COST
        
        # Weighs targets
        weightedTargets = []
        for targetFac in validTargets:
            weightedTargets.append((targetFac, scoreTarget(targetFac.ID, self.ID)))
        weightedTargets = sorted(weightedTargets, key=lambda x: x[1], reverse=True)
        
        # Prioritizes targets that can be overwhelmed
        overwhelmTargets = []
        ignoreTargets = []
        # Classifies targets
        for targetTup in weightedTargets:
            if (curTroops < 1):
                self.troops = curTroops
                return self.actions
            targetFac = targetTup[0]
            targetStates = simulStates[targetFac.ID]
            ttt = floydWarMatrix[self.ID][targetFac.ID]+1
            tttState = targetStates[ttt]

            # Checks that troops won't arrive before bomb :O
            ignore = False
            for bomb in bombInfo:
                if (bomb.owner == 1):
                    print >> sys.stderr, "Bomb from {0}->{1} arrives in: {2} | Attack arrives in: {3}".format(bomb.origin, bomb.target, bomb.ttt, ttt)
                    if (bomb.target == targetFac.ID and ttt <= bomb.ttt):
                        ignore = True
                        break
            if (ignore):
                ignoreTargets.append(targetFac)
                continue

            targetAttack = False
            targetTroops = 0
            if (tttState.owner == 0): # Neutral Target
                targetTroops = tttState.troops+TROOP_EXCESS_NEUTRAL
                if (targetTroops <= curTroops): # Can overwhelm target
                    targetAttack = True
            else: # Enemy Target
                targetTroops = int((tttState.troops+TROOP_EXCESS_ENEMY)*TROOP_OFFENSIVE_MULTIPLIER)+1
                if (targetTroops <= curTroops): # Can overwhelm target
                    targetAttack = True

            # Adds target to priority list if can be overwhelmed
            if (targetAttack):
                overwhelmTargets.append(targetFac)
                self.actions.append(MOVE([self.ID, targetFac.ID, targetTroops]))
                print >> sys.stderr, self.actions[-1].printCmd()
                curTroops -= targetTroops

        # Attacks targets in weighted order
        for targetTup in weightedTargets:
            if (curTroops < 1):
                self.troops = curTroops
                return self.actions
            targetFac = targetTup[0]
            # Filters targets on ignore list or priority list
            if (targetFac in ignoreTargets or targetFac in overwhelmTargets):
                continue
            targetStates = simulStates[targetFac.ID]
            ttt = floydWarMatrix[self.ID][targetFac.ID]+1
            tttState = targetStates[ttt]
            print >> sys.stderr, "Attacking: {0} | ttt: {1} | tttState: Owner->{2} Troops->{3}".format(targetFac.ID, ttt, tttState.owner, tttState.troops)
            # Determines how many troops to send
            targetAttack = False
            targetTroops = 0
            if (tttState.owner == 0): # Neutral Target
                targetTroops = tttState.troops+TROOP_EXCESS_NEUTRAL
                if (targetTroops <= curTroops): # Can overwhelm target
                    print >> sys.stderr, "Overwhelming..."
                    targetAttack = True
                #EXPERIMENTAL: Disabling suspension of attacks
                # elif (targetTroops <= curTroops+self.production): # Able to target next turn
                #     print("Suspend attacks", file=sys.stderr)
                #     self.troops = curTroops
                #     return self.actions
                else: # Unable to overwhelm target immediately
                    targetTroops = int(self.TROOP_OFFENSIVE*curTroops)
                    print >> sys.stderr, "Cannot overwhelm, sending {0} troops".format(targetTroops)
                    targetAttack = True
            elif (tttState.owner == -1): # Enemy Target
                # We only attack when our attack can overwhelm enemy
                targetTroops = int((tttState.troops+TROOP_EXCESS_ENEMY)*TROOP_OFFENSIVE_MULTIPLIER)+1
                if (targetTroops <= curTroops):
                    print >> sys.stderr, "ENEMY! Sending {0} troops".format(targetTroops)
                    targetAttack = True
            # Issues attack command if available
            if (targetAttack):
                self.actions.append(MOVE([self.ID, targetFac.ID, targetTroops]))
                print >> sys.stderr, self.actions[-1].printCmd()
                curTroops -= targetTroops
        self.troops = curTroops
        return self.actions

    '''
    Upgrade function
        - Sends troops to nearby factories to facilitate their upgrading
    '''
    def upgrade(self, simulStates):
        curTroops = min(self.troops, readMaxAvailTroops(simulStates[self.ID])[0])
        print >> sys.stderr, "Factory {0} Sending troops for Upgrading...|Current Troops: {1}".format(self.ID, curTroops)
        if (curTroops < 1):
            self.troops = curTroops
            return self.actions
        # Scans for nearby factories
        for adj in adjList[self.ID]:
            if (curTroops < 1):
                self.troops = curTroops
                return self.actions
            adjFac = factoryInfo[adj[0]]
            #EXPERIMENTAL: We send units in bulk
            requestTroops = min(curTroops, needed_upgradeTroops(self, adjFac, simulStates))
            # requestTroops = needed_upgradeTroops(self, adjFac, simulStates)
            if (requestTroops > 0 and requestTroops <= curTroops):
                self.actions.append(MOVE([self.ID, adjFac.ID, requestTroops]))
                print >> sys.stderr, self.actions[-1].printCmd()
                curTroops -= requestTroops
        self.troops = curTroops
        return self.actions

    '''
    Redistribution function
        - Scans for nearby friendly factories closer than self to enemy
        - Sends excess troops proportionally to those factories
    '''
    def redistribute(self, simulStates):
        curTroops = min(self.troops, readMaxAvailTroops(simulStates[self.ID])[0])
        print >> sys.stderr, "Factory {0} Redistributing...|Current Troops: {1}".format(self.ID, curTroops)
        if (curTroops < 1):
            return self.actions

        #TODO: If have excess troops, send them off proportionally to nearby friendly factories?
        # Get connected friendly reinforcible factories
        adjMyFactories = [facTup[0] for facTup in adjList[self.ID] if (factoryInfo[facTup[0]].owner == 1)]
        myDistToEnemy = self.closestEnemy()[1]
        print >> sys.stderr, "My distance to enemy: {0}".format(myDistToEnemy)
       
        # Get list of 'frontline' friendly factories
        adjFrontlineFactories = [facID for facID in adjMyFactories if (len([enID for enID in range(NUM_FACTORIES) if factoryInfo[enID].owner == -1]) > 0) and factoryInfo[facID].closestEnemy()[1] < myDistToEnemy]
        weightedFrontlineFactories = []
        for facID in adjFrontlineFactories:
            print >> sys.stderr, "Adjacent factory distance to enemy: {0}".format(factoryInfo[facID].closestEnemy()[1])
            weightedFrontlineFactories.append((facID, scoreRedistribution(facID, self.ID, factoryInfo[facID].closestEnemy()[1])))
        weightedFrontlineFactories = sorted(weightedFrontlineFactories, key=lambda x: x[1], reverse=True)

        # Sends available troops based on score
        totScore = 0
        minScore = MAX_INT
        scoreList = [scoreTup[1] for scoreTup in weightedFrontlineFactories]
        limTroops = 0 if self.production == 3 else FACTORY_UPGRADE_COST
        totTroops = max(0, curTroops - limTroops)
        for score in scoreList: # Get min score
            if (score < minScore):
                minScore = score
        for score in scoreList: # Transform range of scoreList to [0, INF)
            score -= minScore
            totScore += score
        for scoreTup in weightedFrontlineFactories:
            if (curTroops <= limTroops):
                self.troops = curTroops
                return self.actions
            normScore = scoreTup[1] - minScore
            weightedTroops = max(curTroops,int((float)(normScore/max(1,totScore))*totTroops))
            if (weightedTroops <= curTroops):
                self.actions.append(MOVE([self.ID, scoreTup[0], weightedTroops]))
                print >> sys.stderr, self.actions[-1].printCmd()
                curTroops -= weightedTroops

        # Just send whatever amts of troops off to the highest-weighted factory
        if (curTroops > 0 and len(weightedFrontlineFactories) > 0):
            self.actions.append(MOVE([self.ID, weightedFrontlineFactories[0][0], curTroops]))
            print >> sys.stderr, self.actions[-1].printCmd()
            curTroops -= curTroops

        self.troops = curTroops
        return self.actions
