import requests, re, json, os, subprocess, time

class Kaggle:

    def __init__(self, username=None, password=None):
        self.session = requests.Session()
        self.logged_in = False

        if username or password:
            self.login(username, password)


    def login(self, username, password):
        r = self.session.post('https://www.kaggle.com/account/login', 
                              data={'username': username, 'password': password})
        
        error = re.search(r'errors":\["(.+)"\]', r.text)
        if error:
            error = error.group(1)
            raise ValueError(error)
            
        print('Login successful')
        self.logged_in = True    

    def logout(self):
        self.session.get('https://www.kaggle.com/account/logoff')
        self.logged_in = False
        print('Logout successful')

    def accept(self, competition):
        if not self.logged_in:
            raise PermissionError('Not logged in')

        r = self.session.post('https://www.kaggle.com/c/%s/rules/accept.json?doAccept=True' % competition)

        if r.status_code == 404:
            raise ValueError('Competition does not exist.')

        print('Accepted competition rules')

    def list_files(self, competition):
        if not self.logged_in:
            raise PermissionError('Not logged in')

        r = self.session.get('https://www.kaggle.com/c/%s/data' % competition)
        
        if r.status_code == 404:
            raise ValueError('Competition does not exist.')

        data = json.loads(re.search(r'{"activeTab":"data".*}', r.text).group(0))
        files = [file['name'] for file in data['files']]

        return files

    def download(self, competition, files=None, path=None, extract=False, accept=True):
        if not self.logged_in:
            raise PermissionError('Not logged in')

        r = self.session.get('https://www.kaggle.com/c/%s' % competition)
        if r.status_code == 404:
            raise ValueError('Competition does not exist.')

        if accept and re.search(r'"hasAcceptedRules":false', r.text):
            self.accept(competition)

        path = path or os.getcwd()
        if not os.path.isdir(path):
            raise OSError(path + ' is not a directory.')

        files = files or self.list_files(competition)
        for file in files:
            print('Dowloading %s' % file)
            r = self.session.get('https://www.kaggle.com/c/%s/download/%s' % (competition, file), stream=True) 
            if r.status_code == 404:
                raise ValueError('File does not exist.')

            local_file = os.path.join(path, file)
            with open(local_file, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
            
            if extract:
                print('Extracting %s' % local_file)
                if os.name == 'nt':
                     subprocess.call(['c:\python2.7\python2.7.exe', 'c:\python2.7\scripts\patool.', local_file])
                else:
                    subprocess.call(['patool', 'extract', local_file])


    def submit(self, competition, file, accept=True):
        if not self.logged_in:
            raise PermissionError('Not logged in')

        r = self.session.get('https://www.kaggle.com/c/%s' % competition)
        if r.status_code == 404:
            raise ValueError('Competition does not exist.')

        if accept and re.search(r'"hasAcceptedRules":false', r.text):
            self.accept(competition)

        team_id = re.search(r'"team":{"id":(\d+)', r.text).group(1)
        metric = re.search(r'"evaluationAlgorithm":{"id":\d+,"name":"([A-Za-z ]+)', r.text).group(1)

        if not os.path.isfile(file):
            raise OSError('File does not exist')
        
        r = self.session.post('https://www.kaggle.com/blobs/inbox/submissions',
                              data={'fileName': file,
                                    'contentLength': os.path.getsize(file),
                                    'lastModifiedDateUtc': os.path.getmtime(file) * 1000})

        r = self.session.post('https://www.kaggle.com' + r.json()['createUrl'],
                              files={'file': open(file, 'rb')})
        
        r = self.session.post('https://www.kaggle.com/c/%s/submission.json' % competition,
                              data={'blobFileTokens': [r.json()['token']]})

        while True:
            time.sleep(1)

            r = self.session.get('https://www.kaggle.com/c/%s/submissions/status.json?apiVersion=1' % competition)
            status = r.json()

            if status['submissionStatus'] == 'complete':
                print('%s: %s' % (metric, status['publicScoreFormatted']))
                print('Rank: %s' % status['rank'])
                break
            elif status['submissionStatus'] == 'pending':
                continue
            else:
                print('OOps.')
                break
        
        


        