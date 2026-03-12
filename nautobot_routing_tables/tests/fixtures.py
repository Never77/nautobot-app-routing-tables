"""Create fixtures for tests."""

from nautobot_routing_tables.models import NautobotRoutingTablesExampleModel


def create_nautobotroutingtablesexamplemodel():
    """Fixture to create necessary number of NautobotRoutingTablesExampleModel for tests."""
    NautobotRoutingTablesExampleModel.objects.create(name="Test One")
    NautobotRoutingTablesExampleModel.objects.create(name="Test Two")
    NautobotRoutingTablesExampleModel.objects.create(name="Test Three")
