CREATE PROCEDURE get_team_data()
BEGIN
    SELECT t.teamID, t.yearID,
        t.G as gamesPlayed, t.W as wins, t.L as losses,
        t.teamRank as teamRank, t.attendance,
        latest.latestName, latest.latestLeague,
        agg.yearFounded, agg.yearLast
    FROM teams t
    JOIN (
        SELECT teamID, name as latestName, lgID as latestLeague
        FROM teams as t2
        WHERE yearID = (SELECT MAX(yearID) FROM teams WHERE teamID = t2.teamID)
        GROUP BY teamID, name, lgID
    ) latest ON t.teamID = latest.teamID
    JOIN (
        SELECT teamID, MIN(yearID) as yearFounded, MAX(yearID) as yearLast
        FROM teams GROUP BY teamID
    ) agg ON t.teamID = agg.teamID;
END;

CREATE PROCEDURE get_player_season_stats()
BEGIN
    SELECT b.playerID, b.yearID, b.teamID, b.lgID,
        SUM(b.G) as gamesPlayed,
        SUM(s.salary) as totalSalary
    FROM batting b
    LEFT JOIN salaries s ON b.playerID = s.playerID 
        AND b.yearID = s.yearID
    GROUP BY b.playerID, b.yearID, b.teamID, b.lgID;
END;

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
END;

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
END;

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
END;

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
END;

CREATE PROCEDURE add_positions()
BEGIN
    SELECT DISTINCT playerID, POS FROM fielding;
END;