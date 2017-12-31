import requests
import re
import pickle
import os
import subprocess

def login(username, password):
    r = requests.post('https://www.kaggle.com/account/login', 
                          data={'username': username, 
                                'password': password})

    error = re.search(r'errors":\["(.+)"\]', r.text)
    if error: 
        raise ValueError(error.group(1))

    with open('.kgcookies', 'wb') as f:
        pickle.dump(cookies, f)

def logout():
    with load_session() as s:
        s.get('https://www.kaggle.com/account/logoff')
    
    os.remove('.kgcookies')

def load_session():
    s = requests.Session()

    try:
        with open('.kgcookies', 'rb') as f:
             s.cookies = pickle.load(f)
    except OSError:
        raise PermissionError("Not logged in.")

    return s

def get_competition(competition):
    with load_session() as s:
        r = s.get('https://www.kaggle.com/c/' + competition)

        if r.status_code == 404:
            raise ValueError("Competition does not exist")

        return json.loads(re.search(r'{"activeTab":.*}', r.text).group())

def list_files(competition):
    data = get_competition(competition)
    files = [f['name'] for f in data['files']]
    return files

def extract(files):
    if os.name == 'nt':
        subprocess.call(['c:\python2.7\python2.7.exe', 
                         'c:\python2.7\scripts\patool', 
                         'extract'].extend(files))
    else:
        subprocess.call(['patool', 'extract'].extend(files))

def accept(competiton):
    data = get_competition(competition)

    if not data['hasAcceptedRules']:
        with load_session() as s:
            s.post('https://www.kaggle.com/c/%s/rules/accept.json?doAccept=True' % competition)

def download(competition, files=None, extract=False, accept=True):
    if accept: 
        accept(competition)
    
    files = files or list_files(competition)

    with load_session() as s:
        for fname in files:
            r = s.get('https://www.kaggle.com/c/%s/download/%s' % (competition, fname), stream=True)
            
            if r.status_code == 404:
                raise ValueError('File does not exist')

            with open(fname, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk: 
                        f.write(chunk)

    if extract: 
        [extract(f) for f in files]

def register_file(file):
    with load_session() as s:
        r =  s.post('https://www.kaggle.com/blobs/inbox/submissions',
                    data={'fileName': file,
                          'contentLength': os.path.getsize(file),
                          'lastModifiedDateUtc': os.path.getmtime(file) * 1000})
        return r.json()['createUrl']

def upload_file(file, create_url):
    with load_session() as s:
        r = s.post('https://www.kaggle.com' + create_url,
                   files={'file': open(file, 'rb')})
        return r.json()['token']

def submit_file(file, competition, token):
    with load_session() as s:
        s.post('https://www.kaggle.com/c/%s/submission.json' % competition,
               data={'blobFileTokens': [token]})

def check_submission_status(competition):
    while True:
        status = get_competition(competition)['mostRecentSubmissionStatus']

        if status['submissionStatus'] == 'complete':
            return (status['publicScoreFormatted'], '')
        elif status['submissionStatus'] == 'pending':
            time.sleep(1)
        else:
            raise ValueError('Submission not uploaded.')

def submit(self, competition, file, accept=True):
    if accept:
        accept(competition)

    create_url = register_file(file)
    submit_file(file, create_url)

    check_submission_status(competition)
