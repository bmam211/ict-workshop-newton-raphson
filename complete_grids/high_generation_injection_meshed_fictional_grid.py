# source(10kV)-node_0-line(1 ohm)-node_1-load(25*-15 = -375MW)
# node_0 = 10kV
# node_1 = 25kV (should be the answer), node_1 = -15kV (V = 15kV, angle = 180 degrees)

import pandapower as pp
from pandapower.powerflow import LoadflowNotConverged

def add_ring_bus_from_to(grid_data, n_ring_num, is_mesh=False):
    id_end = grid_data.get("id_end")
    buses = list(range(id_end, id_end + n_ring_num))
    grid_data["buses"] += buses
    grid_data["id_end"] = buses[-1] + 1
    grid_data["line_from"].append(buses[0])
    grid_data["line_to"].append(grid_data["mv_bus"])
    grid_data["line_from"] += buses[:-1]
    grid_data["line_to"] += buses[1:]
    if is_mesh:
        grid_data["line_from"].append(buses[0])
        grid_data["line_to"].append(buses[-1])
    

def create_grid_topo():
    n_rings = 2
    n_ring_num = 4
    n_meshes = 1
    is_mesh_list = [True] * n_meshes + [False] * (n_rings-n_meshes)
    grid_data = {"id_end": 10, "mv_bus": 0, "line_from": [], "line_to": [], "buses": []}
    for ring, is_mesh in zip(range(n_rings), is_mesh_list):
        add_ring_bus_from_to(grid_data=grid_data, n_ring_num=n_ring_num, is_mesh=is_mesh)

    return grid_data

def create_pp_grid():
    grid_data = create_grid_topo()
    net = pp.create_empty_network()
    pp.create_bus(net, vn_kv=0.4, index=0)
    pp.create_bus(net, vn_kv=0.4, index=1)
    pp.create_line_from_parameters(
        net,
        from_bus=0,
        to_bus=1,
        length_km=1.0,
        r_ohm_per_km=0.01,
        x_ohm_per_km=0.01,
        c_nf_per_km=0.01,
        g_us_per_km=0.0,
        max_i_ka=100.0
    )
    pp.create_ext_grid(net, bus=0, vm_pu=1.0, va_degree=0.0)

    pp.create_buses(net, nr_buses=len(grid_data["buses"]), vn_kv=0.4, index=grid_data["buses"])
    pp.create_lines(net, from_buses=grid_data["line_from"], to_buses=grid_data["line_to"], length_km=[1.0] * len(grid_data["line_from"]), std_type="NAYY 4x150 SE")
    pp.create_loads(net, buses=grid_data["buses"], p_mw=[0.001] * len(grid_data["buses"]))
    return net

net = create_pp_grid()
pp.runpp(net)
print(net.res_bus)


