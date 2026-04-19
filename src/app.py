import eel
import os
import socket
from queue import Queue
from config_loader import get
from logger import log

class ChatBot:

    started = False
    userinputQueue = Queue()

    def isUserInput():
        return not ChatBot.userinputQueue.empty()

    def popUserInput():
        return ChatBot.userinputQueue.get()

    def close_callback(route, websockets):
        if not websockets:
            ChatBot.started = False

    @eel.expose
    def getUserInput(msg):
        ChatBot.userinputQueue.put(msg)
        log.debug("Chat input: %s", msg)
    
    def close():
        ChatBot.started = False
    
    def addUserMsg(msg):
        try:
            eel.addUserMsg(msg)
        except Exception:
            pass
    
    def addAppMsg(msg):
        try:
            eel.addAppMsg(msg)
        except Exception:
            pass

    def start():
        path = os.path.dirname(os.path.abspath(__file__))
        eel.init(os.path.join(path, 'web'), allowed_extensions=['.js', '.html'])

        # Pick a port that is actually free to avoid OSError 10048 on restart
        preferred_port = get("voice.chat_port", 27005)
        port = preferred_port
        for attempt_port in range(preferred_port, preferred_port + 20):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.bind(('localhost', attempt_port))
                s.close()
                port = attempt_port
                break
            except OSError:
                continue

        try:
            eel.start('index.html', mode='chrome',
                                    host='localhost',
                                    port=port,
                                    block=False,
                                    size=(get("voice.chat_width", 350),
                                          get("voice.chat_height", 480)),
                                    position=(10,100),
                                    disable_cache=True,
                                    close_callback=ChatBot.close_callback)
            ChatBot.started = True
            while ChatBot.started:
                try:
                    eel.sleep(1.0)
                except (SystemExit, KeyboardInterrupt):
                    break
                except Exception:
                    break
        
        except EnvironmentError as e:
            log.error("Could not start eel server: %s", e)
        except Exception as e:
            log.error("ChatBot unexpected error: %s", e)
        finally:
            ChatBot.started = False
