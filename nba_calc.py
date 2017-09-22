def calc_PER(mp=None, three=None, ast=None, factor=None, team_ast=None, team_fg=None, fg=None, fga=None, ft=None, vop=None, tov=None, drb_perc=None, orb=None, stl=None, blk=None, pf=None, lg_ft=None, lg_pf=None, lg_fta=None, lg_pt=None):
    uPER = (1 / mp) * (
		three
		+ (2/3) * ast
		+ (2 - factor * (team_ast / team_fg)) * fg
		+ (FT *0.5 * (1 + (1 - (team_ast / team_fg)) + (2/3) * (team_ast / team_fg)))
		- vop * tov
		- vop * drb_perc * (fga - fg)
		- vop * 0.44 * (0.44 + (0.56 * drb_perc)) * (fta - ft)
		+ vop * (1 - drb_perc) * (trb - orb)
		+ vop * drb_perc * orb
		+ vop * stl
		+ vop * drb_perc * blk
		- PF * ((lg_ft / lg_pf) - 0.44 * (lg_fta / lg_pf) * vop)
    )

    print uPER