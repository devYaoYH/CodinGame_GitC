#include <iostream>
#include <string>
#include <vector>
#include <algorithm>

using namespace std;

typedef pair<int, int> ii;
typedef vector<int> vi;
typedef vector<ii> vii;

/**
 * Auto-generated code below aims at helping you parse
 * the standard input according to the problem statement.
 **/
 
vector<vii> adjList;
vector<int[3]> factoryInfo;
vector<int[5]> troopInfo;

int main()
{
    int factoryCount; // the number of factories
    cin >> factoryCount; cin.ignore();
    for (int i = 0; i < factoryCount; i++) {
        vii newNode;
        newNode.clear();
        adjList.push_back(newNode);
        vi newFactory;
        factoryInfo.push_back(newFactory);
    }
    int linkCount; // the number of links between factories
    cin >> linkCount; cin.ignore();
    for (int i = 0; i < linkCount; i++) {
        int factory1;
        int factory2;
        int distance;
        cin >> factory1 >> factory2 >> distance; cin.ignore();
        ii newPair = make_pair(factory2, distance);
        ii revPair = make_pair(factory1, distance);
        adjList[factory1].push_back(newPair);
        adjList[factory2].push_back(revPair);
    }

    // game loop
    while (1) {
        troopInfo.clear();
        int entityCount; // the number of entities (e.g. factories and troops)
        cin >> entityCount; cin.ignore();
        for (int i = 0; i < entityCount; i++) {
            int entityId;
            string entityType;
            int arg1;
            int arg2;
            int arg3;
            int arg4;
            int arg5;
            cin >> entityId >> entityType >> arg1 >> arg2 >> arg3 >> arg4 >> arg5; cin.ignore();
            if (entityType.compare("FACTORY") == 0) {
                factoryInfo[entityId][0] = arg1;
                factoryInfo[entityId][1] = arg2;
                factoryInfo[entityId][2] = arg3;
            }
            else if (entityType.compare("TROOP") == 0) {
                int[5] newTroopInfo = {arg1, arg2, arg3, arg4, arg5};
                troopInfo.push_back(newTroopInfo);
            }
        }

        // Write an action using cout. DON'T FORGET THE "<< endl"
        // To debug: cerr << "Debug messages..." << endl;
        
        

        // Any valid action, such as "WAIT" or "MOVE source destination cyborgs"
        cout << "WAIT" << endl;
    }
}
