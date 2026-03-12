"""Test NautobotRoutingTablesExampleModel Filter."""

from nautobot.apps.testing import FilterTestCases

from nautobot_routing_tables import filters, models
from nautobot_routing_tables.tests import fixtures


class NautobotRoutingTablesExampleModelFilterTestCase(FilterTestCases.FilterTestCase):  # pylint: disable=too-many-ancestors
    """NautobotRoutingTablesExampleModel Filter Test Case."""

    queryset = models.NautobotRoutingTablesExampleModel.objects.all()
    filterset = filters.NautobotRoutingTablesExampleModelFilterSet
    generic_filter_tests = (
        ("id",),
        ("created",),
        ("last_updated",),
        ("name",),
    )

    @classmethod
    def setUpTestData(cls):
        """Setup test data for NautobotRoutingTablesExampleModel Model."""
        fixtures.create_nautobotroutingtablesexamplemodel()

    def test_q_search_name(self):
        """Test using Q search with name of NautobotRoutingTablesExampleModel."""
        params = {"q": "Test One"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_q_invalid(self):
        """Test using invalid Q search for NautobotRoutingTablesExampleModel."""
        params = {"q": "test-five"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 0)
