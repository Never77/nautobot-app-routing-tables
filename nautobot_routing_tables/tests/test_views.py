"""Unit tests for views."""

from nautobot.apps.testing import ViewTestCases

from nautobot_routing_tables import models
from nautobot_routing_tables.tests import fixtures


class NautobotRoutingTablesExampleModelViewTest(ViewTestCases.PrimaryObjectViewTestCase):
    # pylint: disable=too-many-ancestors
    """Test the NautobotRoutingTablesExampleModel views."""

    model = models.NautobotRoutingTablesExampleModel
    bulk_edit_data = {"description": "Bulk edit views"}
    form_data = {
        "name": "Test 1",
        "description": "Initial model",
    }

    update_data = {
        "name": "Test 2",
        "description": "Updated model",
    }

    @classmethod
    def setUpTestData(cls):
        fixtures.create_nautobotroutingtablesexamplemodel()
