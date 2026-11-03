// No-input repro (python3 tools/formations/repro_select.py tools/formations/repro_attack.dm): one archer (a bow, a quiver
// of 2) ordered at a sleeping goblin 4 tiles east; each second, what its attack order holds.
world
	maxx = 60
	maxy = 60
	maxz = 3
	turf = /turf/grounds/grass
	fps = 10

proc/ReproRun()
	sleep(10)
	var/Player/P = new(locate(30, 30, 1))
	usr = P
	var/mob/Monsters/A = new /mob/Monsters/Human(locate(20, 20, 1))
	A.ChangeOwnership(P)
	A.Age = 20
	A.Hunger = 100
	A.Tiredness = 100
	A.remaster_care_hold = world.time + 100000
	var/obj/Items/Equipment/Weapon/Bows/WoodenBow/B = new(A)
	B.suffix = "(Carrying)"
	A.EquipItem(B)
	var/obj/Items/Equipment/Armour/Quiver/LeatherQuiver/Q = new(A)
	Q.suffix = "(Equipped)"
	A.WearingBack = 1
	for(var/k = 1, k <= 2, k++)
		new /obj/Items/Arrows/MetalArrow(Q)
		Q.Content++
	var/mob/Monsters/E = new /mob/Monsters/Goblin/NPC/Scout(locate(24, 20, 1))
	E.Sleeping = 1
	E.CanWalk = 0
	E.HP = 100000
	E.MAXHP = 100000
	world.log << "REPRO|start|hostile=[RemasterHostile(A, E, 1)]|dist=[get_dist(A, E)]|holds=[A.HoldingWeapon]|arrows=[RemasterQuiverCount(A)]|reach=[RmBowRange(A)]|inview=[(E in oview(RmBowRange(A), A)) ? 1 : 0]"
	P.Selected = list(A)
	P.RemasterAttackOrder(E)
	var/datum/remaster_attack/K = A.remaster_attack
	world.log << "REPRO|order|has=[K ? 1 : 0]|target=[K && K.target ? 1 : 0]|status=[A.remaster_order_status]"
	for(var/t = 1, t <= 80, t++)
		sleep(1)
		if(world.time % 5 == 0) P.RemasterOrdersTick()
		if(t % 10 == 0)
			K = A.remaster_attack
			world.log << "REPRO|t[t]|has=[K ? 1 : 0]|target=[K && K.target ? 1 : 0]|status=[A.remaster_order_status]|at=[A.x],[A.y]|arrows=[RemasterQuiverCount(A)]|dest=[A.destination ? "[A.destination]" : "-"]"
	world.log << "REPRO|done"
