# Databases Final Project - Milestone 1

*By Samuel Johns*

## Assumptions Made

- As per the requirements, I have assumed that I was only to add the Team and TeamSeason models for Milestone 1. Because of this, I removed the franchise foreign key from the TeamSeason model.
- I removed the team_id_br, team_id_lahman45, and team_id_retro fields from the TeamSeason model, as they were not necessary for the project.
- I also removed name from the TeamSeason model, as it can be derived from the Team model (due to most recent name requirement).