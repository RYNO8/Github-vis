from flask import current_app as app
from flask import request, render_template
from github import Github, NamedUser, Repository
import pickle
import string
import time

g = Github("test-user1337", "cyrilhas2iq")
MAX_TIME = 5 # bfs() will take <= 5 seconds
BUFFER = 1000

def bfs(user=None, repo=None):
    """https://en.wikipedia.org/wiki/Breadth-first_search"""
    """NOTE: it would tend to explore friends with more followers"""
    
    # queue
    todo = [user or repo] # list of user objects or repo objects

    # graph representation
    allUsers, allRepos = [], [] # list of of user objects and repo objects
    if user:
        allUsers.append(user)
    if repo:
        allRepos.append(repo)
    edges = set() # set of tuples representing edges user to repo (int, int)
    start = time.time()
    
    while todo and time.time() - start < MAX_TIME:
        curr = todo.pop(0)
        print("Exploring:", curr)
        
        if isinstance(curr, NamedUser.NamedUser):
            for child in list(curr.get_repos()):
                if not child in allRepos:
                    todo.append(child)
                    allRepos.append(child)
                edges.add((allUsers.index(curr), BUFFER + allRepos.index(child)))
                
        elif isinstance(curr, Repository.Repository):
            for child in list(curr.get_contributors()):
                if not child in allUsers:
                    todo.append(child)
                    allUsers.append(child)
                edges.add((allUsers.index(child), BUFFER + allRepos.index(curr)))
                
        else:
            raise Exception
        
    [user.bio for user in allUsers] #retrieves bio data, so it can be pickled
    return allUsers, allRepos, edges

def sanitise(text):
    return text.replace("'", "\\'").replace("\r\n", "<br>")

@app.route("/repo_graph", methods=["GET", "POST"])
def repo_graph():
    """\
USAGE
GET /repo_graph?user=RYNO8
POST /repo_graph {"user": "RYNO8"}
GET /repo_graph?repo=chartjs/Chart.js
POST /repo_graph {"repo": "chartjs/Chart.js"}"""
    user = None
    repo = None
    if request.method == "GET":
        user = request.args.get("user", user)
        repo = request.args.get("repo", repo)
    elif request.method == "POST":
        user = request.form.get("user", user)
        repo = request.form.get("repo", repo)
    if (user == None) == (repo == None): #if (both user / repo) OR (neither user / repo)
        return sanitise("invalid\n" + repo_graph.__doc__)

    try: # cache previous graphs during development / debugging
        if user:
            allUsers, allRepos, edges = pickle.load(open(f"Ryan\\repo_graph_cache\\{user}", "rb"))
        else:
            allUsers, allRepos, edges = pickle.load(open(f"Ryan\\repo_graph_cache\\{repo.replace('/', '+')}", "rb"))
    except FileNotFoundError:
        if user:
            allUsers, allRepos, edges = bfs(user=g.get_user(user))
            pickle.dump((allUsers, allRepos, edges), open(f"Ryan\\repo_graph_cache\\{user}", "wb"))
        else:
            allUsers, allRepos, edges = bfs(repo=g.get_repo(repo))
            pickle.dump((allUsers, allRepos, edges), open(f"Ryan\\repo_graph_cache\\{repo.replace('/', '+')}", "wb"))
    
    return render_template(
        "Ryan/templates/repo_graph.html",
        nodes=", ".join([f"""{{
            id: {i},
            label: '{user.login}',
            value: 12,
            shape: 'circularImage',
            image: '{user.avatar_url}',
            {"title: '" + sanitise(user.bio) + "'," if user.bio else ""}
        }}""" for i, user in enumerate(allUsers)]),
        repos=", ".join([f"""{{
            id: {i},
            label: '{repo.name}',
            value: 1,
            title: 'TODO: tooltip text',
        }}""" for i, repo in enumerate(allRepos, start=BUFFER)]),
        edges=", ".join([f"{{ from: {i[0]}, to: {i[1]} }}" for i in edges])
    )

if __name__ == "__main__":
    raise Exception("Don't run this file on its own. run main.py from the root directory")
