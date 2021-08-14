Introduction
==================


Ddom (dynamic device object model) is a library which creates a object model of devices. Devices consist of child devices which can be plugged together. The idea is to model IT devices (switches, router, firewalls, server, cables) with all their modules, slots and ports and automatically verify compatibility between them.

Eg.: A Switch has slots, in these slots you can plug linecards, fans or powersupplies. Fans and powersupplies have an airflow direction. Linecards have ports. A transceiver can be inserted to a port. A cable can be connected to a transceiver,... and so on.

Features
-----------------

Ddom has following features:
    * automatically generate a object from yaml or python data structure
    * verify airflow direction within a Chassis
    * Find children by various properties
    * verify allowed children
    * verify allowed parents
    * Inheritance of properties

Installation
------------

Install ddom by running:

.. code-block:: bash

    pip3 install ddom


Examples
---------


Create a Nexus 5672UP Chassis and print all port names of slot 1 using find_children and parent property
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python


    #!/usr/bin/env python3
    from ddom import *

    chassis = Chassis("n5k-c5672up", "cisco")
    for port in chassis.find_children("port", {"parent.number": "1"}):
        print(port.name)
    

Create a Nexus 5672UP Chassis and print all port names of slot 1 using find_children
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python


    #!/usr/bin/env python3
    from ddom import *

    chassis = Chassis("n5k-c5672up", "cisco")
    for port in chassis.slot("SLOT-1").supervisor().find_children("port"):
        print(port.name)


Create a Nexus 5672UP Chassis and verify airflow
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python


    #!/usr/bin/env python3
    from ddom import *

    chassis = Chassis("n5k-c5672up", "cisco")

    psu_1 = PowerSupply("nxa-pac-1100w", "cisco")
    psu_2 = PowerSupply("nxa-pac-1100w-b", "cisco")

    chassis.slot("PSU-1").connect(psu_1)
    chassis.slot("PSU-2").connect(psu_2) # this will raise an ddom.InvalidAirFlowError exception 


Create a Nexus 5672UP Chassis and print the port name of a specific port
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python


    #!/usr/bin/env python3
    from ddom import *

    chassis = Chassis("n5k-c5672up", "cisco")

    # by number
    print(chassis.slot("SLOT-1").supervisor().port(1).name)

    # by name
    print(chassis.slot("SLOT-1").supervisor().port("eth1/1").name)

    # by index

    print(chassis.slot("SLOT-1").supervisor().port_index(0).name)


See the unit tests in the test directory for many more examples.


Contribute
----------

- Issue Tracker: https://github.com/jinjamator/ddom/issues
- Source Code: https://github.com/jinjamator/ddom

Roadmap
-----------------

Selected Roadmap items:
    * add support for more devices
    * add support for cables
    * add class documentation
    * add device path

For documentation please refer to https://simplenetlink.readthedocs.io/en/latest/

License
-----------------

This project is licensed under the Apache License Version 2.0