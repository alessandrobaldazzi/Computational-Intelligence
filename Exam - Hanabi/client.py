#!/usr/bin/env python3

from sys import argv, stdout
from threading import Thread
import GameData
import socket
from constants import *
import os
import agent

if len(argv) < 4:
    print("Oh no")
    exit(-1)
else:
    ip = argv[1]
    port = int(argv[2])
    playerName = argv[3] #self

run = True

me = ""

statuses = ["Lobby", "Game", "GameHint"]

status = statuses[0]

hintState = ("", "")

def manageInput():
    global run
    global status
    global playerName

    while run:
        #if turn move
        command = input()
        # Choose data to send
        if command == "exit":
            run = False
            os._exit(0)
        elif command == "ready" and status == statuses[0]:
            s.send(GameData.ClientPlayerStartRequest(playerName).serialize())
        elif command == "show" and status == statuses[1]:
            s.send(GameData.ClientGetGameStateRequest(playerName).serialize())
        elif command.split(" ")[0] == "discard" and status == statuses[1]:
            try:
                cardStr = command.split(" ")
                cardOrder = int(cardStr[1])
                s.send(GameData.ClientPlayerDiscardCardRequest(playerName, cardOrder).serialize())
            except:
                print("Maybe you wanted to type 'discard <num>'?")
                continue
        elif command.split(" ")[0] == "play" and status == statuses[1]:
            try:
                cardStr = command.split(" ")
                cardOrder = int(cardStr[1])
                s.send(GameData.ClientPlayerPlayCardRequest(playerName, cardOrder).serialize())
            except:
                print("Maybe you wanted to type 'play <num>'?")
                continue
        elif command.split(" ")[0] == "hint" and status == statuses[1]:
            try:
                destination = command.split(" ")[2]
                t = command.split(" ")[1].lower()
                if t != "colour" and t != "color" and t != "value":
                    print("Error: type can be 'color' or 'value'")
                    continue
                value = command.split(" ")[3].lower()
                if t == "value":
                    value = int(value)
                    if int(value) > 5 or int(value) < 1:
                        print("Error: card values can range from 1 to 5")
                        continue
                else:
                    if value not in ["green", "red", "blue", "yellow", "white"]:
                        print("Error: card color can only be green, red, blue, yellow or white")
                        continue
                s.send(GameData.ClientHintData(playerName, destination, t, value).serialize())
            except:
                print("Maybe you wanted to type 'hint <type> <destinatary> <value>'?")
                continue
        elif command == "":
            print("[" + playerName + " - " + status + "]: ", end="")
        else:
            print("Unknown command: " + command)
            continue
        stdout.flush()

#funzions to send moves to server
def sendHint(destination, type, value):
    s.send(GameData.ClientHintData(playerName, destination, type, value).serialize())

def play(card):
    s.send(GameData.ClientPlayerPlayCardRequest(playerName, card).serialize())

def discard(card):
    s.send(GameData.ClientPlayerDiscardCardRequest(playerName, card).serialize())


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    request = GameData.ClientPlayerAddData(playerName)
    s.connect((HOST, PORT))
    s.send(request.serialize())
    data = s.recv(DATASIZE)
    data = GameData.GameData.deserialize(data)
    if type(data) is GameData.ServerPlayerConnectionOk:
        print("Connection accepted by the server. Welcome " + playerName)
    print("[" + playerName + " - " + status + "]: ", end="")
    Thread(target=manageInput).start()
    

    s.send(GameData.ClientPlayerStartRequest(playerName).serialize()) #auto-ready

    first = 1
    bufferHint = []
    #main cycle for game
    while run:
        dataOk = False

        data = s.recv(DATASIZE)
        data = GameData.GameData.deserialize(data)
        
        if not data:
            continue

        if type(data) is GameData.ServerPlayerStartRequestAccepted:
            dataOk = True
            print("Ready: " + str(data.acceptedStartRequests) + "/"  + str(data.connectedPlayers) + " players")

            data = s.recv(DATASIZE)
            data = GameData.GameData.deserialize(data)

        if type(data) is GameData.ServerStartGameData:
            dataOk = True
            print("Game start!")

            #starting cards in hand
            cards = 4 if len(data.players) > 3 else 5
            #init player
            me = agent.Player(cards, argv[3])

            s.send(GameData.ClientPlayerReadyData(playerName).serialize())
            status = statuses[1]
            
            
            s.send(GameData.ClientGetGameStateRequest(playerName).serialize()) #show for start game
            first = 1

        
        if type(data) is GameData.ServerGameStateData:
            #sync mechanism for first show
            if first == 1:
                first = 0
                me.startgame(data)
                #manage hint out of sync
                for h in bufferHint:
                    dataOk = True
                    me.update(data)
                    if data.player == playerName:
                        s.send(GameData.ClientGetGameStateRequest(playerName).serialize())
                bufferHint.clear()
            
            dataOk = True
            #update player info with show information
            me.update(data)

            #if player turn -> select move and act
            if data.currentPlayer == playerName:
                move = me.play()

                if move[0]["type"]=="hint":
                    sendHint(move[0]["player"], move[0]["hintType"], move[0]["value"])
                elif move[0]["type"] == "play":
                    play(move[0]["card"])
                else:
                    discard(move[0]["card"])

        if type(data) is GameData.ServerActionInvalid and first==0:
            dataOk = True
            #something happened check if everything is ok + useful updates
            s.send(GameData.ClientGetGameStateRequest(playerName).serialize())
        
        if type(data) is GameData.ServerActionValid and first==0:
            dataOk = True
            #someone discarded -> check and update
            me.update(data)

            if data.player == playerName:
                s.send(GameData.ClientGetGameStateRequest(playerName).serialize())
                
         
        if type(data) is GameData.ServerPlayerMoveOk and first==0:
            dataOk = True

            #someone made a move -> check and update
            me.update(data)
        
            if data.player == playerName:
                s.send(GameData.ClientGetGameStateRequest(playerName).serialize())
                


        if type(data) is GameData.ServerPlayerThunderStrike:
            dataOk = True
            print("wrong card played: ", data.lastPlayer, "played ", data.card.value, data.card.color)

            #someone made a mistake -> check and update
            me.update(data)
            
            if data.player == playerName:
                s.send(GameData.ClientGetGameStateRequest(playerName).serialize())
                

        if type(data) is GameData.ServerHintData:
            if first == 1:
                bufferHint.append(data)
            else:
                dataOk = True

                #someone sent a hint -> check and update
                me.update(data)
                
                if data.player == playerName:
                    s.send(GameData.ClientGetGameStateRequest(playerName).serialize())
            
        if type(data) is GameData.ServerInvalidDataReceived:
            dataOk = True
            print(data.data)
        
        if type(data) is GameData.ServerGameOver:
            dataOk = True

            #endgame

            print(data.message)
            print(data.score)
            print(data.scoreMessage)
            stdout.flush()
            run = False
            print("GG\n")
            
        if not dataOk:
            print("Unknown or unimplemented data type: " +  str(type(data)))

        stdout.flush()