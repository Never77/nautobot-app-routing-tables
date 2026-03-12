"""Test nautobotroutingtablesexamplemodel forms."""

from django.test import TestCase

from nautobot_routing_tables import forms


class NautobotRoutingTablesExampleModelTest(TestCase):
    """Test NautobotRoutingTablesExampleModel forms."""

    def test_specifying_all_fields_success(self):
        form = forms.NautobotRoutingTablesExampleModelForm(
            data={
                "name": "Development",
                "description": "Development Testing",
            }
        )
        self.assertTrue(form.is_valid())
        self.assertTrue(form.save())

    def test_specifying_only_required_success(self):
        form = forms.NautobotRoutingTablesExampleModelForm(
            data={
                "name": "Development",
            }
        )
        self.assertTrue(form.is_valid())
        self.assertTrue(form.save())

    def test_validate_name_nautobotroutingtablesexamplemodel_is_required(self):
        form = forms.NautobotRoutingTablesExampleModelForm(data={"description": "Development Testing"})
        self.assertFalse(form.is_valid())
        self.assertIn("This field is required.", form.errors["name"])
