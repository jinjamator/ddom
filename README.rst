



# print('-----------------' )
# for port in chassis.find_children('port'):
#     print(f"{ port.name} is type {port.pid} with transceiver {port._children[0].pid if port._children else '<n/a>'} which has a {port._children[0].socket_type if port._children else '<n/a>'} socket")

# print('-----------------' )
# for psu in chassis.find_children("*",{
#     "pid":r"nxa-pac-.*",
#     "parent.name":r"PSU-2"}):
#     print(psu.name)
# print('-----------------' )

