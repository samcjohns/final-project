import os
import sys
import django
import mysql.connector
import time
from datetime import datetime

# Add the project root directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'my_mlb.settings')
django.setup()

from mlb_data.models import Player, Position, PlayerSeason, BattingStats, FieldingStats, PitchingStats, CatchingStats, Team, TeamSeason

def connect_to_original_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="password",
        database="mlb_original"
    )

# Create stored procedure to get team data with most recent name
def create_stored_procedures():
    conn = connect_to_original_db()
    cursor = conn.cursor()

    # get_team_data()
    cursor.execute("DROP PROCEDURE IF EXISTS get_team_data")
    cursor.execute("""
        CREATE PROCEDURE get_team_data()
        BEGIN
            SELECT t.*, latest.latestName
            FROM teams t
            INNER JOIN (
                SELECT teamID, name AS latestName
                FROM teams t2
                WHERE yearID = (
                    SELECT MAX(yearID) FROM teams WHERE teamID = t2.teamID
                )
                GROUP BY teamID, name
            ) AS latest ON t.teamID = latest.teamID;
        END
    """)

    # get_player_season_stats()
    cursor.execute("DROP PROCEDURE IF EXISTS get_player_season_stats")
    cursor.execute("""
        CREATE PROCEDURE get_player_season_stats()
        BEGIN
            SELECT b.playerID, b.yearID, b.teamID, b.lgID,
                SUM(b.G) as gamesPlayed,
                SUM(s.salary) as totalSalary
            FROM batting b
            LEFT JOIN salaries s ON b.playerID = s.playerID 
                AND b.yearID = s.yearID
            GROUP BY b.playerID, b.yearID, b.teamID, b.lgID;
        END
    """)

    # get_batting_stats()
    cursor.execute("DROP PROCEDURE IF EXISTS get_batting_stats")
    cursor.execute("""
        CREATE PROCEDURE get_batting_stats()
        BEGIN
            select playerID, yearID,
            sum(AB) as atBats, 
            sum(H) as hits, 
            sum(`2B`) as doubles,
            sum(`3B`) as triples, 
            sum(HR) as homeRuns,
            sum(RBI) as runsBattedIn, 
            sum(SO) as strikeouts,
            sum(BB) as walks, 
            sum(HBP) as hitByPitch, 
            sum(IBB) as intentionalWalks, 
            sum(SB) as steals, 
            sum(CS) as stealsAttempted
            from batting
            group by playerID, yearID;
        END
    """)

    # get_fielding_stats()
    cursor.execute("DROP PROCEDURE IF EXISTS get_fielding_stats")
    cursor.execute("""
        CREATE PROCEDURE get_fielding_stats()
        BEGIN
            SELECT playerID, yearID,
                SUM(E) as errors,
                SUM(PO) as putOuts,
                SUM(CASE WHEN POS = 'C' THEN PB ELSE 0 END) as passedBalls,
                SUM(CASE WHEN POS = 'C' THEN WP ELSE 0 END) as wildPitches,
                SUM(CASE WHEN POS = 'C' THEN SB ELSE 0 END) as stealsAllowed,
                SUM(CASE WHEN POS = 'C' THEN CS ELSE 0 END) as stealsCaught,
                MAX(CASE WHEN POS = 'C' THEN 1 ELSE 0 END) as isCatcher
            FROM fielding
            GROUP BY playerID, yearID;
        END
    """)

    # get_pitching_stats()
    cursor.execute("DROP PROCEDURE IF EXISTS get_pitching_stats")
    cursor.execute("""
        CREATE PROCEDURE get_pitching_stats()
        BEGIN
            select playerID, yearID,
                    sum(IPOuts) as outsPitched,
                    sum(ER) as earnedRunsAllowed, 
                    sum(HR) as homeRunsAllowed, 
                    sum(SO) as strikeouts, 
                    sum(BB) as walks, 
                    sum(W) as wins, 
                    sum(L) as losses, 
                    sum(WP) as wildPitches, 
                    sum(BFP) as battersFaced, 
                    sum(HBP) as hitBatters, 
                    sum(SV) as saves
            from pitching 
            group by playerID, yearID;
        END
    """)

    # retrieve_players()
    cursor.execute("DROP PROCEDURE IF EXISTS retrieve_players")
    cursor.execute("""
        CREATE PROCEDURE retrieve_players()
        BEGIN
            SELECT  playerId, 
                    nameFirst, 
                    nameLast, 
                    nameGiven, 
                    birthDay, 
                    birthMonth, 
                    birthYear, 
                    deathDay, 
                    deathMonth, 
                    deathYear, 
                    bats, 
                    throws, 
                    birthCity, 
                    birthState, 
                    birthCountry, 
                    debut, 
                    finalGame 
            FROM people;
        END
    """)

    # add_postions()
    cursor.execute("DROP PROCEDURE IF EXISTS add_positions")
    cursor.execute("""
        CREATE PROCEDURE add_positions()
        BEGIN
            SELECT DISTINCT playerID, POS FROM fielding;
        END
    """)

    conn.commit()
    cursor.close()
    conn.close()

def add_positions(players):
    # First, ensure all positions exist in the new database
    positions = {
        'P': 'Pitcher',
        'C': 'Catcher',
        '1B': 'First Base',
        '2B': 'Second Base',
        '3B': 'Third Base',
        'SS': 'Shortstop',
        'OF': 'Outfield',
        'LF': 'Left Field', # Not Used
        'CF': 'Center Field', # Not Used
        'RF': 'Right Field', # Not Used
        'DH': 'Designated Hitter' # Not Used
    }
    
    # Create all position objects if they don't exist
    for code in positions:
        Position.objects.get_or_create(position_code=code)

    # Connect to original database
    conn = connect_to_original_db()
    cursor = conn.cursor(dictionary=True)

    cursor.callproc('add_positions')
    
    # Only add positions for players we've already created
    # This is more inefficient than the old method, but it allows me 
    # to use a stored procedure and filter in Python instead of in SQL
    for result in cursor.stored_results():
        for row in result.fetchall():
            player = players.get(row['playerID'])
            if player is None:
                continue
            try:
                position = Position.objects.get(position_code=row['POS'].strip())
                player.positions.add(position)
                print(f"Added position {position.position_code} to {player.name}")
            except Position.DoesNotExist:
                print(f"Position {row['POS']} not found for player {player.name}")
    
    cursor.close()
    conn.close()

def retrieve_players():
    # Connect to original database
    conn = connect_to_original_db()
    cursor = conn.cursor(dictionary=True)  # Returns results as dictionaries
    
    players = {}
    # Query to get all players
    cursor.callproc('retrieve_players')
    
    # Iterate through results and create Player instances
    for result in cursor.stored_results():
        for row in result.fetchall():
            # Convert string dates to Python date objects, handling NULL values
            pid = row['playerId']
            first_name = row['nameFirst']
            last_name = row['nameLast']

            # If the playerId or name is non-existant, skip.
            if (pid is None or not pid or
                first_name is None or not first_name or 
                last_name is None or not last_name) :
                continue
            
            if (row['birthYear'] is None) : 
                continue
            # Some players only have a birth year.
            elif (row['birthMonth'] is None or row['birthDay'] is None) :
                birth_day = datetime(year=row['birthYear'], month=1, day=1)
            else:
                birth_day = datetime(year=row['birthYear'], 
                                month=row['birthMonth'],
                                day=row['birthDay'])

            if (row['deathYear'] is None) :
                death_day = None 
            elif (row['deathMonth'] is None or row['deathDay'] is None) :
                death_day = datetime(year=row['deathYear'], month=1, day=1)
            else:
                death_day = datetime(year=row['deathYear'], 
                                month=row['deathMonth'],
                                day=row['deathDay'])
            first_game = datetime.strptime(row['debut'], '%Y-%m-%d').date() if row['debut'] else None
            last_game = datetime.strptime(row['finalGame'], '%Y-%m-%d').date() if row['finalGame'] else None
            
            # Create new Player instance
            player = Player.objects.create(
                name=first_name + " " + last_name,
                given_name=row['nameGiven'],
                birthdate=birth_day,
                deathdate=death_day,
                batting_hand=row['bats'],
                throwing_hand=row['throws'],
                birth_city=row['birthCity'],
                birth_state=row['birthState'],
                birth_country=row['birthCountry'],
                first_game=first_game,
                last_game=last_game
            )
            players[pid] = player
            print(f"Created player: {player.name}")
    
    cursor.close()
    conn.close()

    # Add positions after creating players
    add_positions(players)

    return players

def add_seasons(players):
    conn = connect_to_original_db()
    cursor = conn.cursor(dictionary=True)

    # Combined query to get games played and salary data in one go
    cursor.callproc('get_player_season_stats')
    for result in cursor.stored_results():
        for row in result.fetchall():
            pid = row['playerID']
            yid = row['yearID']
            tid = row['teamID']

            p = players.get(pid)
            if p is None:
                continue

            ps = p.seasons.filter(year=yid).first()
            if ps is None:
                ps = PlayerSeason.objects.create(
                    player=p,
                    year=yid,
                    games_played=row['gamesPlayed'],
                    salary=row['totalSalary'] if row['totalSalary'] is not None else 0
                )
            else:
                ps.games_played += row['gamesPlayed']
                if row['totalSalary']:  # Only update salary if it exists
                    ps.salary += row['totalSalary'] 
                ps.save()
            print(f"Created player-season: {pid}, {yid}")

    cursor.close()
    conn.close()

def add_batting_stats(players):
    conn = connect_to_original_db()
    cursor = conn.cursor(dictionary=True)  # Returns results as dictionaries

    # Query to get discover info each player season
    # Use stored procedure
    cursor.callproc('get_batting_stats')

    for result in cursor.stored_results():
        for row in result.fetchall():
            pid = row['playerID']
            yid = row['yearID']
            p = players.get(pid)
            if p is None:
                continue
            ps = p.seasons.filter(year=yid).first()
            if ps is not None:
                BattingStats.objects.create(
                    player_season=ps,
                    at_bats=row['atBats'],
                    hits=row['hits'],
                    doubles=row['doubles'],
                    triples=row['triples'],
                    home_runs=row['homeRuns'],
                    runs_batted_in=row['runsBattedIn'],
                    strikeouts=row['strikeouts'],
                    walks=row['walks'],
                    hits_by_pitch=row['hitByPitch'],
                    intentional_walks=row['intentionalWalks'],
                    steals=row['steals'],
                    steals_attempted=row['stealsAttempted']
                )
                print(f"Added batting stats to {p.name}'s {yid} season")

    cursor.close()
    conn.close()

def add_fielding_stats(players):
    conn = connect_to_original_db()
    cursor = conn.cursor(dictionary=True)

    # Combined query for both fielding and catching stats
    cursor.callproc('get_fielding_stats')

    for result in cursor.stored_results():
        for row in result.fetchall():
            pid = row['playerID']
            yid = row['yearID']
            p = players.get(pid)
            if p is None:
                continue
            
            ps = p.seasons.filter(year=yid).first()
            if ps is not None:
                # Create fielding stats for all players
                FieldingStats.objects.create(
                    player_season=ps,
                    errors=row['errors'],
                    put_outs=row['putOuts']
                )
                print(f"Added fielding stats to {p.name}'s {yid} season")

                # Create catching stats only if they played as catcher
                if row['isCatcher']:
                    CatchingStats.objects.create(
                        player_season=ps,
                        passed_balls=row['passedBalls'],
                        wild_pitches=row['wildPitches'],
                        steals_allowed=row['stealsAllowed'],
                        steals_caught=row['stealsCaught']
                    )
                    print(f"Added catching stats to {p.name}'s {yid} season")

    cursor.close()
    conn.close()

def add_pitching_stats(players):
    conn = connect_to_original_db()
    cursor = conn.cursor(dictionary=True)

    # Query to get discover info each player season
    cursor.callproc('get_pitching_stats')

    for result in cursor.stored_results():
        for row in result.fetchall():
            pid = row['playerID']
            yid = row['yearID']
            p = players.get(pid)
            if p is None:
                continue
            ps = p.seasons.filter(year=yid).first()
            if ps is not None:
                PitchingStats.objects.create(
                    player_season=ps,
                    outs_pitched=row['outsPitched'],
                    earned_runs_allowed=row['earnedRunsAllowed'],
                    home_runs_allowed=row['homeRunsAllowed'],
                    strikeouts=row['strikeouts'],
                    walks=row['walks'],
                    wins=row['wins'],
                    losses=row['losses'],
                    wild_pitches=row['wildPitches'],
                    batters_faced=row['battersFaced'],
                    hit_batters=row['hitBatters'],
                    saves=row['saves']
                )
                print(f"Added pitching stats to {p.name}'s {yid} season")

    cursor.close()
    conn.close()

def retrieve_teams():
    conn = connect_to_original_db()
    cursor = conn.cursor(dictionary=True)

    # Use stored procedure
    # Gets all team info and most recent name
    cursor.callproc('get_team_data')

    # Build teams and seasons
    teams = {}
    for result in cursor.stored_results():
        for row in result.fetchall():
            tid = row['teamID']

            # If missing, create Team with most recent name
            if tid not in teams:
                teams[tid] = Team.objects.create(
                    team_code=tid,
                    name=row['latestName']
                )
                print(f"Created team: {tid} ({teams[tid].name})")

            # Create a TeamSeason for every row
            TeamSeason.objects.create(
                team=teams[tid],
                year=row['yearID'],
                lg_id=row['lgID'],
                div_id=row['divID'],
                rank=row['teamRank'],
                games=row['G'],
                games_home=row['Ghome'],
                wins=row['W'],
                losses=row['L'],
                div_win=row['DivWin'],
                wc_win=row['WCWin'],
                lg_win=row['LgWin'],
                ws_win=row['WSWin'],
                runs=row['R'],
                at_bats=row['AB'],
                hits=row['H'],
                doubles=row['2B'],
                triples=row['3B'],
                home_runs=row['HR'],
                walks=row['BB'],
                strikeouts=row['SO'],
                stolen_bases=row['SB'],
                caught_stealing=row['CS'],
                hit_by_pitch=row['HBP'],
                sacrifice_flies=row['SF'],
                runs_allowed=row['RA'],
                earned_runs=row['ER'],
                era=row['ERA'],
                complete_games=row['CG'],
                shutouts=row['SHO'],
                saves=row['SV'],
                ip_outs=row['IPouts'],
                hits_allowed=row['HA'],
                home_runs_allowed=row['HRA'],
                walks_allowed=row['BBA'],
                strikeouts_against=row['SOA'],
                errors=row['E'],
                double_plays=row['DP'],
                fielding_pct=row['FP'],
                park=row['park'],
                attendance=row['attendance'],
                bpf=row['BPF'],
                ppf=row['PPF']
            )
            print(f"Created team season: {tid}, {row['yearID']}")

    cursor.close()
    conn.close()
    return teams

# Main function
if __name__ == "__main__":
    start_time = time.time()

    # store procedures
    create_stored_procedures()

    # Retrieve teams first
    teams = retrieve_teams()

    players = retrieve_players()
    add_seasons(players)
    add_batting_stats(players)
    add_fielding_stats(players)
    add_pitching_stats(players)
    # persist all the objects

    end_time = time.time()
    duration = end_time - start_time
    print(f"Conversion took {duration:.2f} seconds")