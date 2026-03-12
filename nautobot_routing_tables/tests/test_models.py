"""Test NautobotRoutingTablesExampleModel."""

from nautobot.apps.testing import ModelTestCases

from nautobot_routing_tables import models
from nautobot_routing_tables.tests import fixtures


class TestNautobotRoutingTablesExampleModel(ModelTestCases.BaseModelTestCase):
    """Test NautobotRoutingTablesExampleModel."""

    model = models.NautobotRoutingTablesExampleModel

    @classmethod
    def setUpTestData(cls):
        """Create test data for NautobotRoutingTablesExampleModel Model."""
        super().setUpTestData()
        # Create 3 objects for the model test cases.
        fixtures.create_nautobotroutingtablesexamplemodel()

    def test_create_nautobotroutingtablesexamplemodel_only_required(self):
        """Create with only required fields, and validate null description and __str__."""
        nautobotroutingtablesexamplemodel = models.NautobotRoutingTablesExampleModel.objects.create(name="Development")
        self.assertEqual(nautobotroutingtablesexamplemodel.name, "Development")
        self.assertEqual(nautobotroutingtablesexamplemodel.description, "")
        self.assertEqual(str(nautobotroutingtablesexamplemodel), "Development")

    def test_create_nautobotroutingtablesexamplemodel_all_fields_success(self):
        """Create NautobotRoutingTablesExampleModel with all fields."""
        nautobotroutingtablesexamplemodel = models.NautobotRoutingTablesExampleModel.objects.create(name="Development", description="Development Test")
        self.assertEqual(nautobotroutingtablesexamplemodel.name, "Development")
        self.assertEqual(nautobotroutingtablesexamplemodel.description, "Development Test")
