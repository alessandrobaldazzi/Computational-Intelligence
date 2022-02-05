import numpy as np

colors = ["red","white","blue","yellow","green"]    # Same as agent.py colors



#######################################################################################################################
#
# Function that calculate possible moves and select the effective move to send to the server
#
# Args:
#  
#   - population: list of possible play/discard moves
#   - hintMoves: list of possible hint moves
#   - hint: the number of hint tokens already used
#   - errors: the red tokens counter
#   - hand: the current hand of the player, useful for the decisional process
#   - states: the states for every card in game, useful for the decisional process
#
# Return: 
# 
#   - move: tuple containing the selected move to play at index 0
#
#######################################################################################################################

def selectMoves(population, hintMoves, hint, errors, hand, states):

    availableMoves = []             # List containing the final moves considered
    
    # To use hint as a move reward parameter we wanted a function that started slow and near a certain value grew fast
    # We decided to use the function  y = 1/(n-x) - 1/n  (where x is hint and n is the maximum value of hint)
    # We used 8.5 instead of 8 to have a high value when missing hints, but not going to infinity 
    p = 1/(8.5 - hint) - 1/8.5
           
    if hint > 7:    # This is just to make the hints more valuable when very near to 8 (only 1 or less tokens remaining)
        
        p *= 2

    e = 3**errors + 1   # Also we assign a move reward parameter also for the errors, as we want to risk, but not too much

    if hint == 0:       # If we have all hints available we exclude the discard moves
        
        population = list(filter(lambda n : n["type"] == "play", population))
    
    
    population = playCard(population, hand, e, p, hint, states)     # We assign a reward to every play/discard move
    
    if hint != 8:   # If the hint tokens are different from 0, we calulate the reward also for the hint moves 
        
        hintMoves = sendHint(hintMoves, p)
        
    availableMoves.extend(population)
    availableMoves.extend(hintMoves)
    availableMoves = sorted(availableMoves, key = lambda p: p["reward"], reverse = True)    #We sort by reward
    
    # We filter out all moves where the reward is too different from the best one
    # In the current situation the range is between 0 and 1 from the first
    # The value can be increased to 2 without any notable difference, but a larger number is usually not optimal 
    # The more it's increased, the more moves can be selected even if not optimal, but there is more risk to select 
    #   an unrewarding move
    # The reason is to find a middle ground between a greedy strategy and a completely probabilistic one 
    availableMoves = list(filter(lambda b : availableMoves[0]["reward"] - b["reward"] <= 1, availableMoves))
    probsMoves = []
    total = 0
    offset = availableMoves[-1]["reward"]
    
    # If we have some negative moves but not all of them, we eliminate the negative ones
    if availableMoves[0]["reward"] > 0 and offset < 0:
        
        availableMoves = list(filter(lambda m : m["reward"] > 0.0, availableMoves))
    
    # If, because of a particularly difficult situation, all moves we can make are negative, we select the better one 
    elif availableMoves[0]["reward"] < 0:
        
        tmp = []
        tmp.append(availableMoves[0])
        availableMoves.clear()
        availableMoves.append(tmp[0])
    
    # We calculate a probability of selection weighted on the rewards, and select pseudo-randomly using the np.random.choice
    # This is to prevent an always greedy strategy, because can take to a local optima
    for key in availableMoves:
        
        total += key["reward"] + offset * (-1) * int(availableMoves[0]["reward"] < 0)
    
    for key in availableMoves:
        
        probsMoves.append((key["reward"] + offset * (-1) * int(availableMoves[0]["reward"] < 0))/total)

    move = np.random.choice(availableMoves, 1, probsMoves)

    return move



#######################################################################################################################
#
# Function that calculates the reward for playing or discarding a given card in hand
#
# Args:
#  
#   - population: list of available moves according to data
#   - hand: cards in hand
#   - e: parameter for error penalties, used to avoid unfavorable random picks
#   - p: parameter for token recovery, used to prevent erratic behavior
#   - hint: number of hint tokens used
#   - states: the states for every card in game, useful for the decisional process
#
# Return: 
# 
#   - population: list of available moves with relative reward value attached
#
#######################################################################################################################

def playCard(population, hand, e, p, hint, states):

    global colors

    # Analyze each move separately
    for mov in population:
        
        # Play moves
        if mov["type"] == "play":
            
            totreward = 0
            totlosePoints = 0
            
            for i in range(len(mov["valcol"])):
                
                if mov["valcol"][i][0] == 5:
                    # Bonus points for playing a 5, thanks to the extra hint token
                    totreward += (1 + p) * mov["chance"][i]
                
                else:
                    # Bonus points for high probabilities of successful play
                    totreward += mov["chance"][i]
            
            for i in range(5):
                
                for j in range(5):
                    
                    notInMove = True
                    
                    for k in mov["valcol"]:
                        
                        if (k[0] == i + 1 and k[1] == colors[j]):
                            
                            notInMove = False
                    # For every possible value not considered by the move, I add a penalty for the possibility 
                    #   to play critical values
                    # This penalty is equal to the points that have been surely lost by the move
                    if notInMove and states[i,j] > 2 and hand[mov["card"]].probs[i,j] != 0:
                        # Penalties for guesses: if many critical cards would lead to an error if played, penalties become larger           
                        totlosePoints += (6 - (i + 1)) * (hand[mov["card"]].probs[i,j])
            # Final reward calculation: we sum the reward and decrease by a penalty (corresponding to the guessing 
            #   penalty and the wrong move penalty)
            mov["reward"] = totreward - totlosePoints - (1 - sum(mov["chance"])) * e
            
            if sum(mov["chance"]) == 1:
                # Big bonus for safe moves, useful to make the playable cards disappear quickly from the hand
                mov["reward"] += 2
        
        elif hint != 0:             # if discarding is an option (tokens are not full)
            
            totreward = 0
            totlosePoints = 0
            
            for i in range(len(mov["valcol"])):
                
                if mov["critical"][i] == 1:

                    # Penalties for discarding critical cards: many lost points lead to larger penalties
                    # To avoid unnecessary discards of critical cards, the penalty is higher than the number of max points lost
                    # A critical card can still be discarded in very very difficult situations
                    totreward += (p - (8 - mov["valcol"][i][0])) * mov["chance"][i]
                
                else:
                    #  If non critical cards, discard is a safe move, but rewarding only if many tokens have been used
                    totreward += p * mov["chance"][i]

            for i in range(5):
                
                for j in range(5):
                    
                    notInMove = True
                    
                    for k in mov["valcol"]:
                        
                        if (k[0] == i+1 and k[1] == colors[j]):
                            
                            notInMove = False
                    
                    if notInMove and states[i,j] > 2 and hand[mov["card"]].probs[i,j] != 0:
                        # If card is not playable and critical, penalties depending on the amount of lost points
                        totlosePoints += (6 - (i + 1)) * (hand[mov["card"]].probs[i,j])

            mov["reward"] = totreward - totlosePoints

    return population



#######################################################################################################################
#
# Function that calculates the reward for playing or discarding a given card in hand
#
# Args:
#  
#   - hintMoves: cards in hand
#   - p: parameter for token usage, used to prevent wasting tokens
#
# Return: 
# 
#   - hintMoves: list of available hints with relative reward value attached
#
#######################################################################################################################

def sendHint(hintMoves, p):

    for m in hintMoves:

        tot = 0
        pointsaved = 0
        
        for i in range(m["cards"]):
            
            if m["critical"][i] == 1:
                # Bonus points for suggesting important critical cards (5s and in general higher values)
                pointsaved += 6 - m["cardValue"][i]
                
            if m["playable"][i] == 1:
                # Bonus points for suggesting playable cards
                pointsaved += 1 + p * int(m["cardValue"][i] == 5)
                
        if pointsaved == 0:
            # Penalty for less useful hints, suggesting discardable cards should be done only if no better moves are available
            pointsaved = -0.3
            
        tot = pointsaved - p
        m["reward"] = tot
        
    return hintMoves