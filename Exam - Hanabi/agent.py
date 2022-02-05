from moves import selectMoves
import GameData
import numpy as np
import copy 

players = 0  #number of players
colors = ["red","white","blue","yellow","green"] #list used as correspondance color -> index
table = [0,0,0,0,0]                         #table with currently played cards
deckAvailableOthers = np.array([            #number of cards in the deck for which all players know the status
                        [3,3,3,3,3],
                        [2,2,2,2,2],
                        [2,2,2,2,2],
                        [2,2,2,2,2],
                        [1,1,1,1,1]
                    ], dtype = "uint") 
population = []                             #selected moves in the play/discard type
hintMoves = []                              #selected moves in hint type 
hint = 0                                    #used hints -> blue tokens utilized
errors = 0                                  #number of red tokens 
memory = []                                 #list used to check if we already counted in our deck the cards of which 
                                            #we have perfect informations



#######################################################################################################################
#
# Class Card: represent a single card in game
#   
# Attributes:
#   - value: value of the card, if certain
#   - color: color of the card, if certain
#   - probs: probability matrix with a value for every card. 
#       Every position is the probability of the current card to be the one corresponding to the indexes:
#           +row: value of the card (conversion is value = index+1)
#           +column: color of the card (the conversion between index and string is made using the colors list )
# 
#######################################################################################################################

class Card(object):
        
    global colors
    global memory
    
    value = 0               
    color = ""              
    probs = np.array([      
        [-1,-1,-1,-1,-1],
        [-1,-1,-1,-1,-1],
        [-1,-1,-1,-1,-1],
        [-1,-1,-1,-1,-1],
        [-1,-1,-1,-1,-1]
    ], dtype = "float")
    

    
    #######################################################################################################################
    #
    # Constructor 
    #
    #######################################################################################################################
    
    def __init__(self) -> None:
        super().__init__()
    
    
    
    #######################################################################################################################
    #
    # Function to deepcopy a card 
    #
    # Args:
    #  
    #   - none
    #
    # Return: 
    # 
    #   - c: copied Card object
    #
    #######################################################################################################################
    
    def copy(self): 
        c = Card()
        c.value = self.value
        c.color = self.color
        c.probs = copy.deepcopy(self.probs) #copy.deepcopy very useful, solved many reference problems everywhere
        return c


        
    #######################################################################################################################
    #
    # Function to mask matrices and filter probabilities according to game state
    #
    # Args: 
    #       
    #   - probs: probabilitiy matrix to be masked
    #   - deck: matrix describing the current state of cards during game (count cards)
    # 
    # Return:
    # 
    #   - Masked matrix with probabilities set to zero for impossible occurrencies
    #
    #######################################################################################################################
    
    def mask(self, probs, deck):                                            #used to constuct a masked array of the deck, 
                                                                            #where cards with probability 0 are removed
        res2 = np.ma.make_mask(probs)                                       #init mask with probabilities
        res3 = np.ma.masked_array(deck, np.invert(res2), fill_value = 0)    #mask elements and filter out impossible occurrences
        return res3.filled()                                                #masked values are swapped with fill_value
    

    
    #######################################################################################################################
    #
    # Function to calculate the probability matrix Probs, if any relevant change happens
    #
    # Args:
    #  
    #   - deck: deck matrix utilized for the calculation, 
    #       can be deckAvailableSelf for the player or deckAvailableOthers for the teammates
    #
    # Return: 
    # 
    #   - none
    #
    #######################################################################################################################
    
    def calcProb(self, deck):
        if self.value == 0 or self.color == "":         #the calculation is not done if we already know all about the card
            tot = 0
            m = self.mask(self.probs, deck)
            tot = np.sum(m)
            self.probs = m/tot
            if self.probs.max() == 1.0:                 #manage the case in which the new probabilities are 1 for a single card
                indexes = np.where(self.probs == 1.0)   
                row = indexes[0][0]
                col = indexes[1][0]
                self.value = row + 1
                self.color = colors[col]
            

            
    #######################################################################################################################
    #
    # Function to calculate ne card probabilities with received hint and new information
    #
    # Args:
    #  
    #   - hint: hint object sent by server
    #       + hint.type             value or color (hint type)
    #       + hint.destination      player to receive hint
    #       + hint.value            number or string (hinted value)
    #       + hint.positions        indexes of target cards in hand
    #   - mypos: card index in hand
    #   - deck: deck matrix utilized for the calculation, 
    #       can be deckAvailableSelf for the player or deckAvailableOthers for the teammates
    #
    # Return: 
    # 
    #   - none
    #
    #######################################################################################################################
    
    def calcHint(self, hint, mypos, deck):
        
        if hint.type == "value" and self.value == 0:            #hint type selector -> value                            
            if mypos in hint.positions:                         #card is targeted by hint
                self.value = hint.value                         #set value of object fo easier access
                for x in range(5):
                    if(x != hint.value - 1):                      
                        self.probs[x, :] = 0                    #set other probabilities to zero
            else:
                self.probs[hint.value - 1, :] = 0               #card is not targeted by hint
                self.calcProb(deck)                             #update probabilities
                isValue = np.sum(self.probs, axis = 1)          #checks if a value is found by exclusion
                x = np.where(isValue == 1)[0]
                if x.size != 0:
                    self.value = x[0] + 1
                
                    
        elif hint.type == "color" and self.color == "":         #hint type selector -> value
            if mypos in hint.positions:                         #card is targeted by hint
                self.color = hint.value                         #set value of object fo easier access
                for i in range(5):
                    if colors[i] != hint.value:
                        self.probs[:,i] = 0                     #set other probabilities to zero
            else:
                i = colors.index(hint.value)
                self.probs[:,i] = 0                             #card is not targeted by hint
                self.calcProb(deck)                             #update probabilities
                isColor = np.sum(self.probs, axis = 0)          #checks if a color is found by exclusion
                y = np.where(isColor == 1)[0]
                if y.size != 0:
                    self.color=colors[y[0]]
        self.calcProb(deck)                                     #update probabilities
        
             
                
#######################################################################################################################
#
# Class Player: represent the player and all his known informations
#   
# Attributes:
#   - hand: list with 4 to 5 Card objects, reprensent the current hand of the player
#   - name: name of the player
#   - first: boolean used to check if everything is initialized correctly
#   - toServe: list used to keep track of unmanaged hints
#   - deckAvailableSelf: matrix that reprensent the current deck, with the infos known by the player
#   - teammates: dictionary which represent the hand of teammates by name
#       Each entry contains:
#           + value: known value of the card, at the index 0
#           + color: known color of the card, at the index 1
#           + card: card object representing the infos known by the corresponding teammate, at the index 2
#   - states: matrix representing the game state of any card
#       The states can be:
#           + 0: the card is not in the game anymore
#           + 1: the card is discardable and not playable
#           + 2: the card is playable and not critical
#           + 3: the card is critical and not playable
#           + 4: the card is critical and playable
# 
#######################################################################################################################

class Player(object):  
    
    global hint
    global errors
    global colors
    global table
    global deckAvailableOthers
    global memory
    
    hand = []
    name = ""
    first = 0
    toServe = []
    deckAvailableSelf = np.array([
        [3,3,3,3,3],
        [2,2,2,2,2],
        [2,2,2,2,2],
        [2,2,2,2,2],
        [1,1,1,1,1]
    ], dtype="uint")
    teammates= {}
    states = np.array([   #row = value  column = color
        [2,2,2,2,2],
        [1,1,1,1,1],
        [1,1,1,1,1],
        [1,1,1,1,1],
        [3,3,3,3,3]
    ], dtype="uint")



    #######################################################################################################################
    #
    # Constructor 
    #
    # Args:
    #   - cards: number of cards of the game, can be 4 or 5 depending of the number of players
    #   - name: name of the player
    #
    #######################################################################################################################

    def __init__(self, cards, name) -> None:
        super().__init__()
        self.name = name
        for _ in range(cards):
            newCard = Card()
            self.hand.append(newCard)
         

         
    #######################################################################################################################
    #
    # Function to initialize internal variables to keep track of the game
    #
    # Args:
    #  
    #   - data: game state object sent by server
    #       + data.players          list of players and relative cards in hand
    #       + players.name          name of the player
    #       + players.hand          list of cards in hand of player
    #
    # Return: 
    # 
    #   - none
    #
    #######################################################################################################################
         
    def startgame(self, data):
        for key in data.players:
            name = key.name
            if name != self.name:                           #if player is a teammate
                hand = []
                for c in key.hand:                          #initialize hands for players
                    newCard = Card()
                    self.deckAvailableSelf[c.value - 1, colors.index(c.color)] -= 1       
                    newCard.calcProb(deckAvailableOthers)        #initialize card probabilities
                    hand.append([c.value, c.color, copy.deepcopy(newCard)])
                self.teammates[name] = copy.deepcopy(hand)



    #######################################################################################################################
    #
    # Function to keep track of the states of single cards: allow to detect critical and playable cards
    #
    # Args:
    #  
    #   - i: index of value (card value -1)
    #   - j: index of the color (using internal reference)
    #
    # Return: 
    # 
    #   - none
    #
    #######################################################################################################################
    
    def newStates(self, i, j):
        if(i == 5):                                             #exit condition for recursion
            return
        if(deckAvailableOthers[i,j] != 0):                      #if there are still cards in play
            play = (i == table[j])
            if i + 1 <= table[j]:
                crit = False
            elif i != 0 and i + 1 > table[j] and self.states[table[j]:i + 1,j].min() == 0:
                crit = False
                play = False
            else :
                crit = deckAvailableOthers[i][j] == 1
            if(not crit and not play):                          #discardable
                self.states[i,j] = 1
            elif(crit and not play):                            #critical not playable
                self.states[i,j] = 3
            elif(play and not crit):                            #playable not critical
                self.states[i,j] = 2
            else:
                self.states[i,j] = 4                            #playable and critical
        else:
            self.states[i,j] = 0                                #not in game anymore
        self.newStates(i + 1, j)                                #recursion
        

    
    #######################################################################################################################
    #
    # Main function to sync with server data and game state
    #
    # Args:
    #  
    #   - data: game state object sent by server
    #       + data.players          list of players and relative cards in hand
    #       + players.name          name of the player
    #       + players.hand          list of cards in hand of player
    #       + currentplayer         player turn
    #       + tablecards            cards played correctly
    #       + discardPile           cards discarded or played
    #       + usedNoteToken         number of hint tokens used
    #       + usedStormTokens       number of errors
    #
    # Return: 
    # 
    #   - none
    #
    #######################################################################################################################
   
    def update(self, data):
        
        global hint
        global errors
        global deckAvailableOthers
        global memory

        if(type(data) is GameData.ServerGameStateData):                         

            hint = data.usedNoteTokens                          #update global variables
            errors = data.usedStormTokens

            for player in self.toServe:                         #update players whose hand changed since player's last turn

                card = copy.deepcopy([p for p in data.players if p.name == player][0].hand[-1])         #take last drawn card (only one per turn)
                self.deckAvailableSelf[card.value - 1, colors.index(card.color)] -= 1                   #remove from cards available to player
                tuple = [card.value, card.color, copy.deepcopy(self.teammates[player][-1][2])]          #adapt
                tuple[2].calcProb(deckAvailableOthers)                                                  #calculate probabilities
                self.teammates[player].pop(-1)                                                          #remove placeholder
                self.teammates[player].append(copy.deepcopy(tuple))                                     #add real card
                self.newStates(card.value - 1, colors.index(card.color))                                #update states
                
            self.toServe.clear()
                 
            if self.first == 0:                                                     #init variables for first show
                
                self.first = 1
                
                for i in range(len(self.hand)):
                    
                    memory.append(0)
                    self.hand[i].calcProb(self.deckAvailableSelf)                   #calculate probabilities for cards in hand 

        elif(type(data) is GameData.ServerActionValid 
            or type(data) is GameData.ServerPlayerThunderStrike
            or type(data) is GameData.ServerPlayerMoveOk):

            if type(data) is GameData.ServerPlayerMoveOk:
                
                table[colors.index(data.card.color)]= data.card.value               #update table

            if(data.lastPlayer == self.name):                                       #if player -> remove played card from cards available
                
                if(memory[data.cardHandIndex] != 1):                                #only if did not have perfect information
                    
                    self.deckAvailableSelf[data.card.value - 1, colors.index(data.card.color)] -= 1
                
                deckAvailableOthers[data.card.value - 1, colors.index(data.card.color)] -=1         #update played cards
                memory.pop(data.cardHandIndex)                                      #remove memory of hand
                memory.append(0)                                                    #init new card memory
                self.newStates(data.card.value - 1, colors.index(data.card.color))  #update states

            else:                                                                   #if teammate
                
                self.toServe.append(data.lastPlayer)
                deckAvailableOthers[data.card.value - 1, colors.index(data.card.color)] -=1         #update played cards
                
                for i in range(len(self.teammates[data.lastPlayer])):                               #update teammate hand
                    
                    if(self.teammates[data.lastPlayer][i][0] == (data.card.value) 
                        and self.teammates[data.lastPlayer][i][1] == data.card.color 
                        and data.cardHandIndex == i):
                        
                        self.newStates(data.card.value - 1,colors.index(data.card.color))
                        
                        if(data.card.value - 1 != 4):
                            
                            self.newStates(data.card.value, colors.index(data.card.color))
                        
                        self.teammates[data.lastPlayer].pop(i)                                      #remove card from teammate hand
                        tuple = [0, "", Card()]                                                     #insert placeholder
                        tuple[2].calcProb(deckAvailableOthers)                                      #this will save hint data
                        self.teammates[data.lastPlayer].append(tuple)
        
        elif(type(data) is GameData.ServerHintData ):
            
            if data.destination == self.name:                                   #if player was target of hint
                
                redo = 0
                
                for i in range(len(self.hand)):
                    
                    self.hand[i].calcHint(data, i, self.deckAvailableSelf)      #calculate new information
                    
                    if self.hand[i].probs.max() == 1.0 and memory[i] != 1:      #if fard value found by exclusion
                        
                        memory[i] = 1                                           #now the player has perfect information
                        redo = 1
                        self.deckAvailableSelf[self.hand[i].value - 1, colors.index(self.hand[i].color)] -= 1
                
                if redo:                                                        #card found by exclusion removes probabilities
                    
                    for i in range(len(self.hand)):
                        
                        self.hand[i].calcProb(self.deckAvailableSelf)           #update probabilities for self
                    
                    for player in self.teammates:
                        
                        for c in self.teammates[player]:
                            
                            c[2].calcProb(deckAvailableOthers)                  #update probabilities for others
            
            else:                                                               #if player was not target
                
                for i in range(len(self.hand)):
                    
                    self.teammates[data.destination][i][2].calcHint(data, i, deckAvailableOthers)   #update probabilities for teammate

                    
    
    #######################################################################################################################
    #
    # Function that calculate possible hint moves for critical cards.
    # A card is considered critical if in state 3 or 4
    #
    # Args:
    #  
    #   - none
    #
    # Return: 
    # 
    #   - none
    #
    #######################################################################################################################
    
    def criticalHint(self):

        # Hint move structure
        moveType = {
                "type":"hint",
                "hintType":"",
                "player":"",
                "value":0,
                "cards":0,    
                "critical":[],
                "playable":[],
                "cardValue":[],
                "cardColor": []
            }
        
        for key in self.teammates.keys():                           # We check every teammate
            
            hand = self.teammates[key]
            
            for c in hand:                                          # We check every card of the hand
                # The isUseful calculation is used to check if the teammate already know the state of his card
                
                stat = -1                                            
                isUseful = False                                     
                
                for i in range(5):
                    
                    for j in range(5):
                        # It's checked if all possible states for the card are the same
                        
                        if c[2].probs[i,j] > 0:
                            
                            if stat == -1:
                            
                                stat = self.states[i,j]
                            
                            else:
                                # If the possible values of the card have different states, the hint can be useful, so it's calculated 
                                
                                if stat != self.states[i,j]:
                                    
                                    isUseful = True                 
                
                # It's checked if:
                #   - the hint is useful
                #   - the state for the card is critical (>2)
                #   - the probability of the card is different from 0 (not the card) or 1 (certainly the card)
                if (isUseful and self.states[c[0] - 1,colors.index(c[1])] > 2 
                    and c[2].probs[c[0] - 1,colors.index(c[1])] !=0 
                    and c[2].probs[c[0] - 1,colors.index(c[1])] !=1 ):
                    
                    append = 0

            # We check if the sum of the values probabilities is 0 or 1, that would mean we have already hinted that value
                    if (c[2].value == 0 
                        and np.sum(c[2].probs[c[0] - 1]) !=0 
                        and np.sum(c[2].probs[c[0] - 1]) !=1):
                        
                        move = copy.deepcopy(moveType)
                        move["player"] = key
                        move["cards"] = 1
                        move["critical"].append(1)
                        move["playable"].append(int(self.states[c[0]-1,colors.index(c[1])]==4))
                        move["cardValue"].append(c[0])
                        move["cardColor"].append(c[1])
                        move["hintType"] = "value" 
                        move["value"] = c[0]

                # If we already calculated a certain hint we don't add it as new hint, but merge it to the existing one
                        for hint in hintMoves:
                            
                            if (hint["player"] == move["player"] 
                                and hint["hintType"] == move["hintType"] 
                                and hint["value"] == move["value"]):
                                
                                hint["cards"] += 1
                                hint["critical"].append(1)
                                hint["playable"].append(int(self.states[c[0] - 1,colors.index(c[1])] == 4))
                                hint["cardValue"].append(c[0])
                                hint["cardColor"].append(c[1])
                                append = 1
                                break
                        
                        if append == 0:
                            
                            hintMoves.append(move)        

                   # Same checks as before but for the color 
                    elif (c[2].color == "" 
                        and np.sum(c[2].probs[:, colors.index(c[1])]) != 0 
                        and np.sum(c[2].probs[:, colors.index(c[1])]) != 1 
                        and self.states[c[0]-1,colors.index(c[1])] == 4):
                        
                        append = 0
                        move2 = copy.deepcopy(moveType)
                        move2["player"] = key
                        move2["cards"] = 1
                        move2["critical"].append(1)
                        move2["playable"].append(int(self.states[c[0]-1,colors.index(c[1])] == 4))
                        move2["cardValue"].append(c[0])
                        move2["cardColor"].append(c[1])
                        move2["hintType"] = "color"
                        move2["value"] = c[1]
                        
                        for hint in hintMoves:
                            
                            if (hint["player"] == move2["player"] 
                                and hint["hintType"] == move2["hintType"] 
                                and hint["value"] == move2["value"]):
                                
                                hint["cards"] += 1
                                hint["critical"].append(1)
                                hint["playable"].append(int(self.states[c[0] - 1,colors.index(c[1])] == 4))
                                hint["cardValue"].append(c[0])
                                hint["cardColor"].append(c[1])
                                append = 1
                                break
                        
                        if append == 0:
                            
                            hintMoves.append(move2) 


        
    #######################################################################################################################
    #
    # Function that calculate possible hint moves for playable cards.
    # A card is considered playable if in state 2 (the 4 state is already considered in the previous function)
    # Almost identical to criticalHint but with a few different checks
    #
    # Args:
    #  
    #   - none
    #
    # Return: 
    # 
    #   - none
    #
    #######################################################################################################################
    
    def playableHint(self):
        
        # Same as criticalHint moveType
        moveType = {
                "type":"hint",
                "hintType":"",
                "player":"",
                "value":0,
                "cards":0,    
                "critical":[],
                "playable":[],
                "cardValue":[],
                "cardColor": []
            }


        for key in self.teammates.keys():
            
            hand = self.teammates[key]
            
            for c in hand:
                
                stat = -1
                isUseful = False
                
                for i in range(5):
                    
                    for j in range(5):
                        
                        if c[2].probs[i,j] > 0:
                            
                            if stat == -1:
                                
                                stat = self.states[i,j]
                            
                            else:
                                
                                if stat != self.states[i,j]:
                                    
                                    isUseful = True
                # The flag is changed to be ==2 (playable not critical) instead of >2 (critical or critical and playable)
                
                if (isUseful and self.states[c[0] - 1,colors.index(c[1])] == 2 
                    and c[2].probs[c[0] - 1,colors.index(c[1])] != 0 
                    and c[2].probs[c[0] - 1,colors.index(c[1])] != 1):
                    
                    append = 0
                    
                    if (c[2].value == 0 
                        and np.sum(c[2].probs[c[0] - 1]) != 0 
                        and np.sum(c[2].probs[c[0] - 1]) != 1):
                        
                        move = copy.deepcopy(moveType)
                        move["player"] = key
                        move["cards"] = 1
                        move["critical"].append(0)
                        move["playable"].append(1)
                        move["cardValue"].append(c[0])
                        move["cardColor"].append(c[1])
                        move["hintType"] = "value" 
                        move["value"] = c[0]

                        for hint in hintMoves:
                            
                            if (hint["player"] == move["player"] 
                                and hint["hintType"] == move["hintType"] 
                                and hint["value"] == move["value"]):
                                
                                hint["cards"] += 1
                                hint["critical"].append(0)
                                hint["playable"].append(1)
                                hint["cardValue"].append(c[0])
                                hint["cardColor"].append(c[1])
                                append = 1
                                break
                        
                        if append == 0:
                            
                            hintMoves.append(move)
 
                    elif (c[2].color == "" 
                        and np.sum(c[2].probs[:, colors.index(c[1])]) != 0 
                        and np.sum(c[2].probs[:, colors.index(c[1])]) != 1):
                        
                        append = 0
                        move2 = copy.deepcopy(moveType)
                        move2["player"] = key
                        move2["cards"] = 1
                        move2["critical"].append(0)
                        move2["playable"].append(1)
                        move2["cardValue"].append(c[0])
                        move2["cardColor"].append(c[1])
                        move2["hintType"] = "color"
                        move2["value"] = c[1]

                        for hint in hintMoves:
                            
                            if ((hint["player"] == move2["player"]) 
                                and (hint["hintType"] == move2["hintType"]) 
                                and (hint["value"] == move2["value"])): 
                                
                                hint["cards"] += 1
                                hint["critical"].append(0)
                                hint["playable"].append(1)
                                hint["cardValue"].append(c[0])
                                hint["cardColor"].append(c[1])
                                append = 1
                                break
                        
                        if append == 0:
                            
                            hintMoves.append(move2)          



    #######################################################################################################################
    #
    # Function that calculate possible hint moves for discardable cards.
    # A card is considered discardable if in state 1 
    # Almost identical to criticalHint but with a few different checks
    # Shouldn't be called very often, because hinting discardable cards is quite of an unrewarding move
    #
    # Args:
    #  
    #   - none
    #
    # Return: 
    # 
    #   - none
    #
    #######################################################################################################################
    
    def discardableHint(self):
        
        # Same as criticalHint moveType
        moveType = {
                "type":"hint",
                "hintType":"",
                "player":"",
                "value":0,
                "cards":0,    
                "critical":[],
                "playable":[],
                "cardValue":[],
                "cardColor": []
            }


        for key in self.teammates.keys():
            
            hand = self.teammates[key]
            
            for c in hand:
                # Similar to criticalHint and playableHint, some different flags
                
                if (self.states[c[0]-1,colors.index(c[1])] == 1 
                    and c[2].probs[c[0] - 1,colors.index(c[1])] != 0 
                    and c[2].probs[c[0] - 1,colors.index(c[1])] != 1):
                    
                    append = 0
                    
                    if (c[2].value == 0 
                        and np.sum(c[2].probs[c[0] - 1]) != 0 
                        and np.sum(c[2].probs[c[0] - 1]) != 1):
                        
                        move = copy.deepcopy(moveType)
                        move["player"] = key
                        move["cards"] = 1
                        move["critical"].append(0)
                        move["playable"].append(0)
                        move["cardValue"].append(c[0])
                        move["cardColor"].append(c[1])
                        move["hintType"] = "value" 
                        move["value"] = c[0]

                        for hint in hintMoves:
                            
                            if (hint["player"] == move["player"] 
                                and hint["hintType"] == move["hintType"] 
                                and hint["value"] == move["value"]):
                                
                                hint["cards"] += 1
                                hint["critical"].append(0)
                                hint["playable"].append(0)
                                hint["cardValue"].append(c[0])
                                hint["cardColor"].append(c[1])
                                append=1
                                break
                        
                        if append == 0:
                            
                            hintMoves.append(move)
 
                    elif (c[2].color == "" 
                        and np.sum(c[2].probs[:, colors.index(c[1])]) != 0 
                        and np.sum(c[2].probs[:, colors.index(c[1])]) != 1):
                        
                        append = 0
                        move2 = copy.deepcopy(moveType)
                        move2["player"] = key
                        move2["cards"] = 1
                        move2["critical"].append(0)
                        move2["playable"].append(0)
                        move2["cardValue"].append(c[0])
                        move2["cardColor"].append(c[1])
                        move2["hintType"] = "color"
                        move2["value"] = c[1]

                        for hint in hintMoves:
                            
                            if ((hint["player"] == move2["player"]) 
                                and (hint["hintType"] == move2["hintType"]) 
                                and (hint["value"] == move2["value"])): 
                                
                                hint["cards"] += 1
                                hint["critical"].append(0)
                                hint["playable"].append(0)
                                hint["cardValue"].append(c[0])
                                hint["cardColor"].append(c[1])
                                append = 1
                                break
                        
                        if append == 0:
                            
                            hintMoves.append(move2)          



    #######################################################################################################################
    #
    # Function that calculate possible play/discard moves for the cards in hand
    #
    # Args:
    #  
    #   - none
    #
    # Return: 
    # 
    #   - none
    #
    #######################################################################################################################
    
    def findMoves(self):
        
        global population
        
        population.clear()

        # Temporary Play/Discard move structure, simplified for the inital pruning but different from the final one
        moveType = {
                "card":0,
                "type":"",
                "critical":0,
                "chance":0,
                "value": 0,
                "color":""
            }
        groupMoves = []         # List used for moves grouping
        effectiveMoves = []     # Another list used as temporary place before extending population 
        move = moveType.copy()

        for card in self.hand:
            
            # If we know for certain the value/color of the card 
            if card.value != 0 and card.color != "":
                
                move = moveType.copy()
                
                # We check if the state for the card is playable or playable-critical
                if (self.states[card.value - 1, colors.index(card.color)] == 2 
                    or self.states[card.value - 1, colors.index(card.color)] == 4):
                    
                    # The play moves are constucted
                    move["card"] = self.hand.index(card)
                    move["type"] = "play"
                    move["chance"] = 1
                    move["critical"] = int(self.states[card.value - 1, colors.index(card.color)] == 4)
                    move["value"] = card.value
                    move["color"] = card.color
                    population.append(move)
                
                # We check if the state for the card is discardable
                elif self.states[card.value - 1, colors.index(card.color)] == 1:
                    
                    # The hint moves are constructed 
                    move["card"] = self.hand.index(card)
                    move["type"] = "discard"
                    move["chance"] = 1
                    move["value"] = card.value
                    move["color"] = card.color
                    population.append(move)
            
            # If we know only the value of the card 
            elif card.value != 0 and card.color == "":
                
                cardTmp = copy.deepcopy(card)
                
                #We check for every color if the card could be played or discarded
                for color in colors:
                    
                    move = moveType.copy()
                    cardTmp.color = color
                    
                    #Same checks as before to construct play and discard moves
                    if ((self.states[cardTmp.value - 1, colors.index(cardTmp.color)] == 2 
                        or self.states[cardTmp.value - 1, colors.index(cardTmp.color)] == 4) 
                        and cardTmp.probs[cardTmp.value - 1,colors.index(cardTmp.color)] != 0):

                        move["card"] = self.hand.index(card)
                        move["type"] = "play"
                        move["chance"] = cardTmp.probs[cardTmp.value - 1, colors.index(cardTmp.color)]
                        move["critical"] = int(self.states[cardTmp.value - 1, colors.index(cardTmp.color)] == 4)
                        move["value"] = cardTmp.value
                        move["color"] = cardTmp.color
                        population.append(move)
                    
                    elif (self.states[cardTmp.value - 1, colors.index(cardTmp.color)] == 1 
                        and cardTmp.probs[cardTmp.value - 1,colors.index(cardTmp.color)] != 0):
                        
                        move["card"] = self.hand.index(card)
                        move["type"] = "discard"
                        move["chance"] = cardTmp.probs[cardTmp.value - 1, colors.index(cardTmp.color)]
                        move["value"] = cardTmp.value
                        move["color"] = cardTmp.color
                        population.append(move)
            
            # If we know only the color of the card, all below follow the same pattern as before
            elif (card.value == 0 
                and card.color != ""):
                
                cardTmp = card.copy()
                
                for i in range(5):
                    
                    move = moveType.copy()
                    cardTmp.value = i+1
                    
                    if ((self.states[cardTmp.value - 1, colors.index(cardTmp.color)] == 2 
                        or self.states[cardTmp.value - 1, colors.index(cardTmp.color)] == 4) 
                        and cardTmp.probs[i,colors.index(cardTmp.color)] != 0):
                        
                        move["card"] = self.hand.index(card)
                        move["type"] = "play"
                        move["chance"] = card.probs[cardTmp.value - 1, colors.index(cardTmp.color)]
                        move["critical"] = int(self.states[cardTmp.value - 1, colors.index(cardTmp.color)] == 4)
                        move["value"] = cardTmp.value
                        move["color"] = cardTmp.color
                        population.append(move)
                    
                    elif (self.states[card.value - 1, colors.index(cardTmp.color)] == 1 
                        and cardTmp.probs[i,colors.index(cardTmp.color)] != 0):
                        
                        move["card"] = self.hand.index(card)
                        move["type"] = "discard"
                        move["chance"] = cardTmp.probs[cardTmp.value - 1, colors.index(cardTmp.color)]
                        move["value"] = cardTmp.value
                        move["color"] = cardTmp.color
                        population.append(move)
            
            # We know only sparse data about the card, so we must check for every option
            elif (card.value == 0 
                and card.color == ""):
                
                m = card.mask(card.probs, self.states)
                cardTmp = card.copy()
                
                for i in range(5):
                    for j in range(5):
                        
                        move = moveType.copy()
                        cardTmp.value = i + 1
                        cardTmp.color = colors[j]
                        
                        if ((m[cardTmp.value - 1, colors.index(cardTmp.color)] == 2 
                            or m[cardTmp.value - 1, colors.index(cardTmp.color)] == 4) 
                            and cardTmp.probs[i,j] != 0):
                            
                            move["card"] = self.hand.index(card)
                            move["type"] = "play"
                            move["chance"] = cardTmp.probs[cardTmp.value - 1, colors.index(cardTmp.color)]
                            move["critical"] = int(m[cardTmp.value-1, colors.index(cardTmp.color)] == 4)
                            move["value"] = cardTmp.value
                            move["color"] = cardTmp.color
                            population.append(move)
                        
                        elif (m[cardTmp.value - 1, colors.index(cardTmp.color)] == 1 
                            and cardTmp.probs[i,j] != 0):
                            
                            move["card"] = self.hand.index(card)
                            move["type"] = "discard"
                            move["chance"] = cardTmp.probs[cardTmp.value - 1, colors.index(cardTmp.color)]
                            move["value"] = cardTmp.value
                            move["color"] = cardTmp.color
                            population.append(move)
        
        # Now that I have all moves I group them, if on the same card and same type
        for i in range(len(self.hand)):
            
            groupMoves = list(filter(lambda m : m["card"] == i and m["type"] == "play", population))
            meeehPlay = {
                "card": i,          # card: index of the card in the hand
                "type":"play",      # type: type of moves
                "critical":[],      # critical: list that append the criticality of a possible card
                "chance":[],        # chance: list that append the chances of a possible card
                "valcol":[]         # valcol: list that append the tuples (value, color) of a possible card
            }
            meeehDiscard = {
                "card": i,
                "type":"discard",
                "critical":[],
                "chance":[],
                "valcol": []
            }

            for mel in groupMoves:
                
                meeehPlay["critical"].append(mel["critical"])
                meeehPlay["chance"].append(mel["chance"])
                meeehPlay["valcol"].append((mel["value"], mel["color"]))
            
            if len(groupMoves) != 0:
                
                effectiveMoves.append(copy.deepcopy(meeehPlay))
            
            groupMoves.clear()
            groupMoves = list(filter(lambda m : m["card"] == i and m["type"] == "discard", population))

            for mel in groupMoves:

                meeehDiscard["critical"].append(mel["critical"])
                meeehDiscard["chance"].append(mel["chance"])
                meeehDiscard["valcol"].append((mel["value"], mel["color"]))

            if len(groupMoves) != 0:
                
                effectiveMoves.append(copy.deepcopy(meeehDiscard))
            
            groupMoves.clear()
            
        population.clear()
        population.extend(copy.deepcopy(effectiveMoves))
        effectiveMoves.clear()

    
    
    #######################################################################################################################
    #
    # Function that calculates discard moves if other moves are not safe enough
    # A card is considered critical if its state is 3 or 4, with 4 being assigned to critical and playable cards
    # Since the player may not find a safe enough move from the data available, he must pick the best discard
    # among the cards in hand
    #
    # Args:
    #  
    #   - none
    #
    # Return: 
    # 
    #   - none
    #
    #######################################################################################################################
    
    def discardIfAllCritical(self):
        
        global population
        
        pop = []                                #temporary population of moves
        moveType = {                            #move structure
                "card":0,
                "type":"discard",
                "critical":1,
                "chance":0,
                "value": 0,
                "color":""
            }
        groupMoves = []
        effectiveMoves = []
        move = moveType.copy()

        for card in self.hand:

            if (card.value != 0 
                and card.color != ""):                  #card has perfect information
                
                move = moveType.copy()
                move["card"] = self.hand.index(card)
                move["chance"] = 1
                move["value"] = card.value
                move["color"] = card.color
                pop.append(copy.deepcopy(move))
                
            elif (card.value != 0                       #player knows value but not color
                and card.color == ""):
                
                cardTmp = copy.deepcopy(card)
                
                for color in colors:
                    
                    move = moveType.copy()
                    cardTmp.color = color
                    move["card"] = self.hand.index(card)
                    move["chance"]=cardTmp.probs[cardTmp.value - 1, colors.index(cardTmp.color)]
                    move["value"] = cardTmp.value
                    move["color"] = cardTmp.color
                    pop.append(copy.deepcopy(move))
            
            elif (card.value == 0                       #player knows color but not value
                and card.color != ""):
                
                cardTmp = copy.deepcopy(card)
                
                for i in range(5):
                    
                    move = moveType.copy()
                    cardTmp.value = i + 1
                    move["card"] = self.hand.index(card)
                    move["chance"] = cardTmp.probs[cardTmp.value - 1, colors.index(cardTmp.color)]
                    move["value"] = cardTmp.value
                    move["color"] = cardTmp.color
                    pop.append(copy.deepcopy(move))
            
            elif (card.value == 0                       #player has only sparse information on card
                and card.color == ""):
                
                cardTmp = copy.deepcopy(card)
                
                for i in range(5):
                    
                    for j in range(5):
                        
                        move = moveType.copy()
                        cardTmp.value = i + 1
                        cardTmp.color = colors[j]
                        move["card"] = self.hand.index(card)
                        move["chance"] = cardTmp.probs[cardTmp.value - 1, colors.index(cardTmp.color)]
                        move["value"] = cardTmp.value
                        move["color"] = cardTmp.color
                        pop.append(copy.deepcopy(move))
        
        for i in range(len(self.hand)):
            
            groupMoves = list(filter(lambda m : m["card"] == i, pop))
            meeehDiscard = {
                "card": i,
                "type":"discard",
                "critical":[],
                "chance":[],
                "valcol": []
            }

            for mel in groupMoves:
                
                meeehDiscard["critical"].append(1)
                meeehDiscard["chance"].append(mel["chance"])
                meeehDiscard["valcol"].append((mel["value"], mel["color"]))
            
            if len(groupMoves) != 0:
                
                effectiveMoves.append(copy.deepcopy(meeehDiscard))
            
            groupMoves.clear()
        
        population.extend(copy.deepcopy(effectiveMoves))
        pop.clear()
        effectiveMoves.clear()



    #######################################################################################################################
    #
    # Function that calculate possible moves and select the effective move to send to the server
    #
    # Args:
    #  
    #   - none
    #
    # Return: 
    # 
    #   - move: tuple containing the selected move to play at index 0
    #
    #######################################################################################################################
    
    def play(self):

        hintMoves.clear()
        
        self.findMoves()    # Select the play discard moves
        
        if hint < 8:          # Select the playable and critical hints only if enough hint tokens are available

            self.playableHint()
            self.criticalHint()

        if len(hintMoves) == 0 and hint < 8: # Select the discardable hints only if enough hint tokens are available and
                                             #    there are no other available hints
            self.discardableHint()

        if len(hintMoves) == 0:              #If no hints are available, we can be obliged to discard a critical card
                                             #   so we select those moves too
            self.discardIfAllCritical()

        move = selectMoves(population, hintMoves, hint, errors, self.hand, self.states)     # Effective decision of the move

        if move[0]["type"] != "hint":     # If we played/discarded we update our hand with an empty card
            
            self.hand.pop(move[0]["card"])
            self.hand.append(Card())
            self.hand[-1].calcProb(self.deckAvailableSelf)
        
        return move