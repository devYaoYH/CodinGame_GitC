# Ghost in the Cell: A CodinGame Contest

First CodinGame contest for me, finished #13 in Legend, pretty happy with my result. Coming in, was really scared by all the talk of GAs/FSM/MCs, none of which I've done before...Still, this particular game lends itself well to simple heuristic methods.

## Strategy Outline:

1. Simulate 20 rounds into the future based on input

2. Simulate enemy actions*

3. Update simulation post-enemy actions

4. Scores enemy targets (using future states) and bombs high-scoring factories

5. Update simulation post-bombing

6. Execute actions (in order):

    1. Reinforce factories
  
    2. Upgrade (if safe to do so -> based on next 10 turn simulation minus the 10 troops required for an upgrade)
  
    3. Attack nearby factories
  
        - Prioritizes those we can immediately capture
    
    4. Send troops to nearby non-fully upgraded factories to facilitate faster upgrading
  
    5. Redistributes troops
  
        - Pushes troops in factories further from the enemy to those closer
    
    6. With what remaining troops left in factories, indiscriminately whack the nearest enemy factory…

## Nuances

- **Target Scoring** Some variation on (1/distance)*production-troops.

- **Floyd-Warshall** Adjusted F-W to ignore links greater than 7 dist (making decisions that far into the game didn't really pan out that well). Also, prioritized path with more factories when dist is the same (so troops will hop rather than directly path towards target).

- **Enemy Simulation** Only simulated steps less than 5 turns into the future. Also, tuned enemy to be more aggressive (*1.53) hence, making my bot more defensive.

- **Offensive Factor** Added a multiplicative factor (1.17) for attacking factories, counters enemy reinforcement and prevents uselessly sending troops against the enemy without achieving much.

- **Magic Numbers** I guess even without implementing a GA, I was a human-GA :P All these magical numbers were the result of many submissions with but a tweak for a single variable haha...

## Analysis:

   *The one step that I think Machine Learning techniques could lend itself to best is in predicting enemy actions. Once we know what the enemy will do, the optimal move is a mathematical outcome. So some prediction-feedback cycle would work well with a good initial seed, slowly tuning itself based on how the opponent chooses differently to attack.
   
   As I didn't manage to come up with a model to learn the enemy's movements in time, how well the enemy's actions concurred with my bot's (static) predictions played a huge part in its success (or failure).
   
   Floyd-Warshall pushed me from ~#100 to top 15. The flexibility in troop hopping multiple factories allows you to change your movement based on changing enemy actions. This avoids the issue of over-committing troops where it could have been otherwise better used.
   
   Troops are an investment, you could attrite the enemy, upgrade your factories or attempt to capture enemy/neutral factories. This game was all about managing such an investment well with bombs thrown in to shake things up (since bombs couldn't be predicted with too much accuracy).
   
   One thing I left out was predicting enemy bombs and evacuating my factories. Oh and sending troops to factory 0 seems to be a simple but effective strategy employed by many top bots >.<

Well, that was a really fun week and I can't wait till the next competition! Thanks *CodinGame* for such great fun :D
