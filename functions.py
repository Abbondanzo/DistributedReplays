# Helper functions
import json
import os
from flask import jsonify, render_template, current_app

# Replay stuff
from objects import Game, PlayerGame, Player
from players import get_rank_batch
from replayanalysis.analysis.saltie_game.saltie_game import SaltieGame as ReplayGame
from replayanalysis.analysis.saltie_game.metadata.ApiPlayer import ApiPlayer as GamePlayer

replay_dir = os.path.join(os.path.dirname(__file__), 'replays')
if not os.path.isdir(replay_dir):
    os.mkdir(replay_dir)
model_dir = os.path.join(os.path.dirname(__file__), 'models')
if not os.path.isdir(model_dir):
    os.mkdir(model_dir)

ALLOWED_EXTENSIONS = {'bin', 'gz'}
json_loc = os.path.join(os.path.dirname(__file__), 'data', 'categorized_items.json')
with open(json_loc, 'r') as f:
    item_dict = json.load(f)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def return_error(msg):
    return render_template('error.html', error=msg)
    # return jsonify({'error': msg})


def get_replay_path(uid, add_extension=True):
    return os.path.join(replay_dir, uid + ('.gz' if add_extension else ''))


rank_cache = {}


def get_item_name_by_id(id_):
    return item_dict[id_]


def get_item_dict():
    return item_dict


def convert_pickle_to_db(game: ReplayGame, offline_redis=None) -> (Game, list, list):
    """
    Converts pickled games into various database objects.

    :param game: Pickled game to process into Database object
    :return: Game db object, PlayerGame array, Player array
    """
    teamsize = len(game.api_game.teams[0].players)
    player_objs = game.api_game.teams[0].players + game.api_game.teams[1].players
    ranks = get_rank_batch([p.id for p in player_objs], offline_redis=offline_redis)
    print ('got ranks')
    rank_list = []
    mmr_list = []
    for r in ranks:
        if 'tier' in r:
            rank_list.append(r['tier'])
        if 'rank_points' in r:
            mmr_list.append(r['rank_points'])
    replay_id = game.api_game.id
    g = Game(hash=replay_id, players=[str(p.id) for p in player_objs],
             ranks=rank_list, mmrs=mmr_list, map=game.api_game.map, team0score=game.api_game.teams[0].score,
             team1score=game.api_game.teams[1].score, teamsize=teamsize, match_date=game.api_game.time) # TODO: add name back
             #name=game.)
    player_games = []
    players = []
    # print('iterating over players')
    for p in player_objs:  # type: GamePlayer
        if isinstance(p.id, list):  # some players have array platform-ids
            p.id = p.id[0]
            print('array id', p.id)
        print ('done checking for array')
        camera = p.cameraSettings
        print ('done with camera settings')
        loadout = p.loadout
        print('loadout done')
        field_of_view = camera.fieldOfView
        transition_speed = camera.transitionSpeed
        pitch = camera.pitch
        swivel_speed = camera.swivelSpeed
        stiffness = camera.stiffness
        height = camera.height
        distance = camera.distance
        pg = PlayerGame(player=p.id, name=p.name, game=replay_id, score=p.matchScore, goals=p.matchGoals, assists=p.matchAssists,
                        saves=p.matchSaves, shots=p.matchShots, field_of_view=field_of_view,
                        transition_speed=transition_speed, pitch=pitch,
                        swivel_speed=swivel_speed, stiffness=stiffness, height=height,
                        distance=distance, car=-1 if loadout is None else loadout.car, is_orange=not p.isOrange,
                        win=game.api_game.teams[int(not p.isOrange)].score > game.api_game.teams[int(p.isOrange)].score)
        player_games.append(pg)
        print('appended player')
        p.id = str(p.id)
        if len(str(p.id)) > 40:
            p.id = p.id[:40]
        p = Player(platformid=p.id, platformname="", avatar="", ranks=[])
        players.append(p)
    print ('returning info')
    return g, player_games, players
