import sys
import os
import configparser
import time
import argparse
import multiprocessing as mp
import re
from pprint import pprint
import googletrans
import unicodedata
import pickle

class controller(object):
    work_dir = ''
    interface = ''
    var = ''

    def __init__(self, work_dir, interface, config):
        self.work_dir = work_dir
        self.interface = interface
        self.config = config

    def run(self):
        self.interface.output('status', f"Working directory is: {self.work_dir}")

        #talk_log = logFile(self.work_dir + '/' + talk_log_path)
        #translate_log = logFile(self.work_dir + '/' + translate_log_path)

        self.interface.output('status', "Createing console_log")
        console_log = logFile(self.config.getConfig('console_log_path'), self.config.getConfig('translation_keyword'))
        self.interface.output('status', "Createing translator")
        translator = translator_worker('en', cache(self.config.getConfig('cache_file'), self.config.getConfig('cache_size')))

        self.interface.output('status', "Run console_log")
        console_log.run()
        self.interface.output('status', "Run translator")
        translator.run()

        self.interface.output('status', "View console log status for 10 sec(ish)")
        oldstatus = ''
        #for i in range(0,1000):
        while True:
            status = console_log.getStatus()
            if status != oldstatus:
                oldstatus = status
                self.interface.output('status', f"console log: {status}")
            if status == 'eof':
                break
            time.sleep(0.001)

        self.interface.output('status', "Get content from console_log")
        chat = chatLog()
        chat.addChat(console_log.getContent())
        
        self.interface.output('status', "Output chat")
        for line in chat.getNewChatLines():
            self.interface.output('chat', f"{line['player']} -> {line['msg']}")

        self.interface.output('status', "Truncate cfg file")
        with open(self.config.getConfig('translate_output_cfg'), 'r') as cfg_file_read:
            lines = cfg_file_read.readlines()
        if len(lines) > 10:
            with open(self.config.getConfig('translate_output_cfg'), 'w') as cfg_file:
                cfg_file.writelines(lines[-10:])

        # Main loop
        oldyou = None
        while True:
            chatLines = chat.getNewChatLines()
            status = console_log.getStatus()
            if status != oldstatus:
                oldstatus = status
                #self.interface.output('status', f"console_log: {status}")
            #if status == 'translate':
            for line in chatLines:
                translator.translate(line)
            if status == 'shutdown':
                break
            else:
                lines = translator.getOutput(maxOutput=5, maxTries=10)
                if len(lines) >= 1:
                    self.interface.output('status', "open CFG")
                    cfg_file = open(self.config.getConfig('translate_output_cfg'), 'a', encoding = 'utf-8', errors = 'replace')
                    for line in lines:
                        self.interface.output('status', f"translator: {translator.getStatus()}")
                        self.interface.output('status', f"write to cfg file: echo {line.player} [{line.src}] >>> {line.text}\n")
                        cfg_file.write(f"echo {line.player} [{line.src}] >>> {line.text}\n")
                    cfg_file.close()
                chat.addChat(console_log.getContent())
                if chat.getYou() and chat.getYou() != oldyou:
                    oldyou = chat.getYou()
                    self.interface.output('status', f"you: {chat.getYou()}")
                for line in chatLines:
                    self.interface.output('chat', f"{line['player']} -> {line['msg']}")
            time.sleep(0.01)


        self.interface.output('status', "Telling console_log to stop")
        console_log.stop()
        self.interface.output('status', "Telling translator to stop")
        translator.stop()

        self.interface.output('status', "End")


               #when console_log.new async
        #    get console log
        #    check if translate trigger
        #        async run translate
        #    check for talk
        #    insert to talk log


class chatLog(object):
    you_search = re.compile(r'^Player: (.*) - Damage (Taken|Given)$')
    you = False
    talk_search = re.compile(r'^(?P<ping_messure>[ ]{10,})?(?P<is_dead>\*DEAD\*[ ]*)?(?P<player>.*). : (?P<msg>.*?)$')
    previousMatch = {'player': '', 'msg': ''}
    chatLines = []
    viewedChatIndex = 0

    def getYou(self):
        return self.you

    def getNewChatLines(self):
        oldViewedChatIndex = self.viewedChatIndex
        self.viewedChatIndex = len(self.chatLines)

        return self.chatLines[oldViewedChatIndex:]

    def addChat(self, lines):
        for line in lines:
            line = "".join(ch for ch in line if unicodedata.category(ch)[0]!="C")
            youSearchResult = self.you_search.search(line)
            if youSearchResult and self.you != youSearchResult.group(1):
                self.you = youSearchResult.group(1)
            else:
                chatSearchResult = self.talk_search.search(line)
                if chatSearchResult and not chatSearchResult.group('player') == self.you and chatSearchResult.group('ping_messure') == None:
                    match = chatSearchResult.groupdict()
                    self.previousMatch = match
                    self.chatLines.append(match)
                
# Config and cache
class config(object):
    config_file_path = ''
    configparser = ''
    config = {
#        'console_log_path': '',
#        'cache_file': '',
#        'cache_size': '',
#        'translate_output_cfg': '',
#        'translation_keyword': ''
    }

    def __init__(self):

        argparser = argparse.ArgumentParser(
            formatter_class = argparse.ArgumentDefaultsHelpFormatter,
            description = "Translator for CSGO.",
            epilog = """
                Config is taken in the following priority (highest first): arguments, config file, built in defaults.
                If you wish to use a non-default path for the config file you must always start the application with that as an argument.
                If the config file does not exist, it will be created with the values of that run, and updates on each consecutive run where config is changed.
            """
        )
        argparser.add_argument('--console-log-path',    type=str, default='csgo/console.log',                                               help="Relative path from current working directory, or full path.")
        argparser.add_argument('--config-file',         type=str, default=f"{os.path.expanduser('~')}/.config/csgo-translator/config.ini",  help="Path to config file.")
        argparser.add_argument('--cache-file',          type=str, default=f"{os.path.expanduser('~')}/.cache/csgo-translator/translations.pkl", help="Path to store cache.")
        argparser.add_argument('--cache-size',          type=int, default=5000,                                                             help="Max translated lines to cache.")
        argparser.add_argument('--translate-output-cfg',type=str, default=f"csgo/cfg/csgo-translate.cfg",                                   help="CSGO cfg file executed to output translated text to console.")
        argparser.add_argument('--translation-keyword', type=str, default=f"csgo-translate.py",                                             help="Keyword in console log to trigger translation.")

        args = argparser.parse_args()

        self.config_file_path = args.config_file

        # Create dir and file for config file
        if not os.path.exists(os.path.dirname(args.config_file)):
            os.makedirs(os.path.dirname(self.config_file_path))
        if not os.path.isfile(self.config_file_path):
            open(self.config_file_path, 'w').close()

        # Read in config from file if nothing has been set by parameters
        self.configparser = configparser.ConfigParser()
        self.configparser.add_section('main')
        with open(self.config_file_path, 'r') as config_file:
            self.configparser.read_file(config_file)

        # Console log path
        if args.console_log_path == argparser.get_default('console_log_path'):
            self.setConfig('console_log_path', self.configparser.get('main', 'console_log_path', fallback = args.console_log_path))
        else:
            self.setConfig('console_log_path', args.console_log_path)

        # Cache path
        if args.cache_file == argparser.get_default('cache_file'):
            self.setConfig('cache_file', self.configparser.get('main', 'cache_file', fallback = args.cache_file))
        else:
            self.setConfig('cache_file', args.cache_file)

        # Max cache lines
        if args.cache_size == argparser.get_default('cache_size'):
            self.setConfig('cache_size',
                    self.configparser.getint('main', 'cache_size', fallback = args.cache_size)
            )
        else:
            self.setConfig('cache_size', args.cache_size)

        # CSGO cfg path
        if args.translate_output_cfg == argparser.get_default('translate_output_cfg'):
            self.setConfig('translate_output_cfg', self.configparser.get('main', 'translate_output_cfg', fallback = args.translate_output_cfg))
        else:
            self.setConfig('translate_output_cfg', args.translate_output_cfg)

        # Translation trigger word
        if args.translation_keyword == argparser.get_default('translation_keyword'):
            self.setConfig('translation_keyword', self.configparser.get('main', 'translation_keyword', fallback = args.translation_keyword))
        else:
            self.setConfig('translation_keyword', args.translation_keyword)

        # Create directory and file for csgo cfg file
        if not os.path.exists(os.path.dirname(self.getConfig('translate_output_cfg'))):
            os.makedirs(os.path.dirname(self.getConfig('translate_output_cfg')))
        if not os.path.isfile(self.getConfig('translate_output_cfg')):
            open(self.getConfig('translate_output_cfg'), 'w').close()
        
        self.writeConfig()

    def setConfig(self, param, value):
        self.config[param] = value
        self.writeConfig()
    def getConfig(self, param):
        return self.config[param]
    def writeConfig(self):
        with open(self.config_file_path, 'w') as config_file:
            self.configparser.write(config_file)

class cache(object):
    cache_file = ''
    cache_size = 0
    cache = []

    def __init__(self, cache_file, cache_size): 

        self.cache_file = cache_file
        self.cache_size = cache_size

        # Create directory for cache
        if not os.path.exists(os.path.dirname(self.cache_file)):
            os.makedirs(os.path.dirname(self.cache_file))
        if not os.path.isfile(self.cache_file):
            open(self.cache_file, 'w').close()
        # Read cache files and populate variables
        self._populateCache()

    # Fully load/save the cache from/to file
    def _populateCache(self):
        with open(self.cache_file, 'rb') as cache_file:
            try:
                self.cache = pickle.load(cache_file)
            except EOFError:
                pass
    def _writeCache(self):
        with open(self.cache_file, 'wb') as cache_file:
            pickle.dump(self.cache, cache_file, pickle.HIGHEST_PROTOCOL)

    def _updateCache(self, cache):
        cache['timestamp'] = time.time()

    #Make cache 1 size smaller than max size
    def truncateCache(self):
        pass
        
    def checkCache(self, origintext=''):
        result = [cache for cache in self.cache if cache['origin'] == origintext]

        if result:
            self._updateCache(result[0])
            return result[0]
        else:
            return False

    # Takes a single cache dict in the format described above, timestamp will be added if missing or replaced if present
    def addCache(self, cache):
        if len(self.cache) > self.cache_size:
            self.truncateCache()
        
        cache['timestamp'] = time.time()
        
        if not cache['src'] or not cache['origin'] or not cache['text']:
            raise Exception(f"cache is missing index: {str(cache)}")

        self.cache.append(cache)
        self._writeCache()
        

class viewConsole():
    def output(self, field, message):
        print('(' + field + ' field) ' + message)

class logFile(object):
    logfile_path = ''
    controlQ = ''
    contentQ = ''
    statusQ = ''
    worker = ''
    status ='new'

    def __init__(self, logfile_path, translation_keyword):
        self.logfile_path = logfile_path
        self.controlQ = mp.Queue()
        self.contentQ = mp.Queue()
        self.statusQ = mp.Queue()
        self.translation_keyword = translation_keyword
        self.worker = mp.Process(target=self._watchFile, args=(self.controlQ, self.contentQ, self.statusQ, self.logfile_path, self.translation_keyword))

    def run(self):
        self.worker.start()
        self.statusQ.put('started')
        i=0 
        while self.contentQ.empty() and i <= 10000:
            time.sleep(0.001)
            i=i+1

    def getStatus(self):
        while not self.statusQ.empty():
            self.status = self.statusQ.get()
        return self.status

    def stop(self):
        self.controlQ.put('stop')
        self.worker.join(int(5))

    def getContent(self, amount=0):
        value = []
        if amount > 0:
            for i in range(amount):
                if not self.contentQ.empty():
                    value.append(self.contentQ.get())
                else:
                    break
        elif amount == 0 and not self.contentQ.empty():
            while not self.contentQ.empty():
                value.append(self.contentQ.get())
        return value

    def _watchFile(self, controlQ, contentQ, statusQ, logfile_path, translation_keyword):
        if not os.path.isfile(logfile_path):
            open(logfile_path, 'w').close()
        #with open(logfile_path, 'r', encoding = 'latin-1') as file_handler:
        with open(logfile_path, 'r', encoding = 'utf-8', errors='replace') as file_handler:
            # Used to let controlQ show that we have reached the end of the file
            status = 'fresh'
            while True:
                time.sleep(0.01)
                while not controlQ.empty():
                    if controlQ.get() == 'stop':
                        print(f"{__name__}: stopping myself")
                        controlQ.close()
                        contentQ.close()
                        statusQ.close()
                        print(f"{__name__}: stopped myself")
                        return 0
                for line in file_handler.readlines():
                    while contentQ.full():
                        time.sleep(0.01)
                    if line.strip():
                        if status != 'appending':
                            statusQ.put('appending')
                            status = 'appending'
                        if line.strip() == 'Host_Shutdown':
                            statusQ.put('shutdown')
                        if line.strip() == translation_keyword:
                            statusQ.put('translate')
                            statusQ.put('idle')
                        contentQ.put(line)
                    
                if status != 'eof':
                    status = 'eof'
                    statusQ.put('eof')


class translator_worker(object):
    targetLang = ''
    controlQ = ''
    inputQ = ''
    outputQ = ''
    statusQ = ''
    worker = ''
    status = 'new'
    oldQstatus = ''

    def __init__(self, targetLang, cache):
        self.targetLang = targetLang
        self.controlQ = mp.Queue()
        self.inputQ = mp.Queue()
        self.outputQ = mp.Queue()
        self.statusQ = mp.Queue()
        self.worker = mp.Process(target=self._translate, args=(self.controlQ, self.inputQ, self.outputQ, self.statusQ, self.targetLang, cache))

    def run(self):
        self.worker.start()
        self.statusQ.put('started')

    def stop(self):
        self.controlQ.put('stop')
        self.worker.join(int(5))

    def translate(self, input):
        self.statusQ.put('translating')
        self.inputQ.put(input)

    def getStatus(self):
        while not self.statusQ.empty():
            self.status = self.statusQ.get()
        return self.status

    def getOutput(self, minOutput=1, maxOutput=0, maxTries=100):
        value = []
        messagesGot = 0
        tries = 0
        while (messagesGot < minOutput or messagesGot < maxOutput) and tries < maxTries:
            Qstatus = str(f"empty: {str(self.outputQ.empty())}, size: {str(self.outputQ.qsize())}, full: {str(self.outputQ.full())}")
            if Qstatus != self.oldQstatus:
                self.oldQstatus = Qstatus
                print(Qstatus)
            time.sleep(0.01)
            if maxOutput > 0:
                for i in range(messagesGot, maxOutput):
                    if not self.outputQ.empty():
                        value.append(self.outputQ.get())
                        messagesGot = messagesGot + 1
                    else:
                        tries = tries + 1
                        break
            elif maxOutput == 0 and not self.outputQ.empty():
                while not self.outputQ.empty():
                    value.append(self.outputQ.get())
                    messagesGot = messagesGot + 1
            elif self.outputQ.empty():
                tries = tries + 1
        return value

    def _translate(self, controlQ, inputQ, outputQ, statusQ, targetLang, cache):
        translator = googletrans.Translator()
        old_inputtext = ''
        old_outputline = ''
        total_translations = 0
        cached_translations = 0
        while True:
            time.sleep(0.01)
            if not controlQ.empty():
                if controlQ.get_nowait() == 'stop':
                    print(f"{__name__}: stopping myself")
                    controlQ.close()
                    inputQ.close()
                    outputQ.close()
                    statusQ.close()
                    print(f"{__name__}: stopped myself")
                    return 0
            while not inputQ.empty():
                # Google ratelimit max 5 / sec
                time.sleep(0.2)
                while outputQ.full():
                    time.sleep(0.1)
                    statusQ.put('full')

                total_translations = total_translations + 1

                inputline = inputQ.get()
                inputtext = inputline['msg']

                old_inputtext = inputtext
                cache_result = cache.checkCache(inputtext)
                if cache_result:
                    statusQ.put(f"cached: {cache_result['text']}")
                    cached_translations = cached_translations + 1

                    statusQ.put(f"cache hits percent: {(cached_translations / total_translations) * 100}")

                    outputline = googletrans.models.Translated(cache_result['src'], targetLang, cache_result['origin'], text = cache_result['text'], pronunciation = 'Unknown')
                else:
                    outputline = translator.translate(inputline['msg'], targetLang)
                    statusQ.put(f"new translation: {outputline.text}")
                    cache.addCache({
                        'src': outputline.src,
                        'origin': outputline.origin,
                        'text': outputline.text
                    })
                old_outputline = outputline
                
                if inputline['player']:
                    outputline.player = inputline['player']
                else :
                    outputline.player = "UNKNOWN"
                outputQ.put(outputline)

if __name__ == '__main__':
    mp.freeze_support()
    mp.set_start_method('spawn')
    console = viewConsole()
    config = config()
    print(os.getenv('PWD'))
    #exit()
    application = controller(os.getenv('PWD'), console, config)
    application.run()