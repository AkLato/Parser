import sys
import os.path
import json
import re
from datetime import datetime


class Parser:
    def __init__(self, source_path):
        # load data into structure
        self.data = self.read(source_path)

        # graphics
        self.menu = """
        ________________________________________
        /    0. vystup [module, text, logLevel]
        /    1. soubor
        /    2. modul
        /    3. casovy interval
        /    4. loglevel
        /    5. fulltext / regex
        /    q. konec
        /    ?. manual
        -------------------------
        """
        self.manual = """
       Volba:
        0 - uzivatel vlozi seznam carkuo oddelenych poli, ktere bude pozadovat na vystupu. Seznam moznosti je na konci 
            zadani u prikladu radku.
        1 - script vyzve uzivatele k zadani nazvu souboru
          - script vypise vsechny zaznamy ktere obsahuji dany soubor v JSON formatu, kdy kazdy zaznam bude obsahovat
            ty casti logu ktere jsou zadane v polozce (0 - vystup)
        2 - script vyzve uzivatele k zadani nazvu modulu
          - vypise stejny vystup jako v prvnim pripade jenom vybere zaznamy pro dany modul
        3 - script vyzve uzivatele k zadani casove (datum a cas) intervalu a vypise zaznamy z tohoto rozsahu, nebo 
            zahlasi chybu ze nebyl nalezen zadny zaznam.
        4 - script vyzve uzivatele k vyberu logLevelu a vypise vsechny zaznamy s danym logLevelem.
        5 - script vyzve uzivatele k zadani textu ktery pak bude hledat ve vsech castech zaznamu a vypise ty ktery
            zadany text obsahuji. Jako vstup muze byt regularni vyraz.
        q - ukonci script
        
        =====================================================
        Keys: [recordId, PID, threadId, datetime, module, logLevel, text, srcFile, srcFileLine] 
        =====================================================
        """

        # run loop
        self.run()

    @staticmethod
    def read(source_path=None):
        """
        Loads file and parses it into a dictionary.
        :return: list of dicts
        """

        def _line_match(pline) -> bool:
            """Bool to decide if new line appears."""
            # TODO for longer logs, it is not possible to expect the "[0" at line beginning condition to hold
            lm = pline.startswith('[0')
            return bool(lm)

        def _yield_matches(full_log):
            """Handle multiline entries."""
            elog = []
            for rline in full_log:
                if _line_match(rline):
                    if len(elog) > 0:
                        yield "\n".join(elog)
                        elog = []
                elog.append(rline)

            yield '\n'.join(elog)

        # try to open file at provided filepath
        output = []
        parser_errs = 0
        if os.path.isfile(source_path):
            with open(source_path, 'r') as log:
                # some entries are on multiple lines
                log_file_obj = log.readlines()
                entry_list = list(_yield_matches(log_file_obj))

                for line in entry_list:
                    line = line.replace('\n', ' ')
                    parse_error = {}
                    # create data structure
                    try:
                        ml_string = line[46:].split(" ")
                        rev_str = line[::-1]
                        data = {
                            'recordId': line[1:7],
                            'PID': line[9:15],
                            'threadId': line[17:25],
                            'datetime': line[27:45],
                            'module': ml_string[0],
                            'logLevel': ml_string[1],
                            'text': re.findall(r".*?- (.*) <.*", line[46:])[0],
                            # re module returns first matching element without overlap, so string was reversed to force
                            # it to match from reverse (install module which supports overlap?)
                            'srcFile': re.findall('[a-zA-Z]+.[a-zA-Z]+', rev_str)[0][::-1],
                            'srcFileLine': re.findall(r'\d+', rev_str)[0][::-1]
                        }
                        output.append(data)
                    except IndexError:
                        parse_error['IndexError'] = "Something went wrong while parsing"
                        output.append(parse_error)
                        parser_errs += 1
                        continue

        else:
            print("Provided input is not valid, exiting.")
            sys.exit()

        print(f"Encountered {parser_errs} errors while parsing.")
        return output

    def run(self):
        """
        Handles command line interface.
        """
        user_menu = {
            '1': 'Provide file name for which entries will be displayed: ',
            '2': 'Provide module name for which entries will be displayed: ',
            '3': 'Provide time interval in format "DD/MM HH:MM:SS.FFF, DD/MM HH:MM:SS.FFF": ',
            '4': 'Provide desired log level: ',
            '5': 'Provide phrase for full text search: '
        }
        flatten = False
        while not flatten:
            print(self.menu)
            user_choice = input("Provide option: ")

            if user_choice == '0':
                # output
                self.final_filter(self.data)
            elif user_choice == '1':
                # file
                self.file_filter(input(user_menu[user_choice]))
            elif user_choice == '2':
                # module
                self.module_filter(input(user_menu[user_choice]))
            elif user_choice == '3':
                # time
                self.time_filter(input(user_menu[user_choice]))
            elif user_choice == '4':
                # log
                self.log_filter(input(user_menu[user_choice]))
            elif user_choice == '5':
                # full search
                self.search_filter(input(user_menu[user_choice]))
            elif user_choice == "?":
                print(self.manual)
            elif user_choice == 'q':
                # q - end script
                flatten = True
            else:
                print(f"Unknown command: {user_choice}")

    @staticmethod
    def final_filter(data):
        """
        Finishing function which prepares the result and prints it.
        """
        user_key_choice = input('Which fields to show? (provide values separated by ","): ').replace(' ', '').split(",")
        result = []
        # filter result so only requested items appear
        for i in data:
            result.append({k: v for k, v in i.items() if k in user_key_choice})

        # print result in readable format
        if result:
            print(json.dumps(result, indent=4))
        else:
            print("No matching entries found.")

        return

    def file_filter(self, file):
        """
        Filters data so that only specified files are present in query. Sends filtered data to final function.
        """
        f_data = list(filter(lambda x: x.get('srcFile', None) in [file], self.data))
        return self.final_filter(f_data)

    def module_filter(self, module):
        """
        Filters data so that only specified modules are present in query. Sends filtered data to final function.
        """
        f_data = list(filter(lambda x: x.get('module', None) in [module], self.data))
        return self.final_filter(f_data)

    def time_filter(self, time):
        """
        Filters data so that only entries within time interval are returned. Sends filtered data to final function.
        """
        time = time.split(",")
        time_start = datetime.strptime(time[0].strip(), '%d/%m %H:%M:%S.%f')
        time_end = datetime.strptime(time[1].strip(), '%d/%m %H:%M:%S.%f')
        res = []
        err_counter = 0

        for i in self.data:
            try:
                entry_timestamp = datetime.strptime(i.get('datetime', None), '%d/%m %H:%M:%S.%f')
                if time_start <= entry_timestamp <= time_end:
                    res.append(i)
            except Exception:
                err_counter += 1
                continue
        print(f"Encountered: {err_counter} errors.")
        return self.final_filter(res)

    def log_filter(self, level):
        """
        Filters data so that only specified logs are present in query. Sends filtered data to final function.
        """
        f_data = list(filter(lambda x: x.get('logLevel', None) in [level], self.data))
        return self.final_filter(f_data)

    def search_filter(self, search):
        """
        Filters data so that only entries with specified text are returned. Sends filtered data to final function.
        """
        res = []

        # decide if searched string is regex or not
        try:
            re.compile(search)
            is_valid = True
        except re.error:
            is_valid = False

        # append only items that contain searched term
        for item in self.data:
            for k, v in item.items():
                if is_valid:
                    if re.search(search, v) is not None:
                        res.append(item)
                else:
                    if search in v:
                        res.append(item)

        # display result
        if res:
            print(json.dumps(res, indent=4))
        else:
            print("No matching entries found.")

        return


if __name__ == "__main__":
    # Parser(sys.argv[1])

    Parser('stream.log')
