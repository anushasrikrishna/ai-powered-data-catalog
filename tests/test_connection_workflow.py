from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from ui import connection_workflow


class TestConnectionWorkflow(unittest.TestCase):
    def test_successful_test_connection_requests_one_rerun_after_registration(self) -> None:
        state = {connection_workflow.STATUS_STATE_KEY: "not_configured"}
        registry = Mock()
        registry.entries.return_value = []
        registry.get.return_value = None

        def complete_connection(*args: object, **kwargs: object) -> None:
            state[connection_workflow.SUCCESS_RERUN_KEY] = True

        with (
            patch.object(connection_workflow.st, "session_state", state),
            patch.object(connection_workflow, "get_connection_registry", return_value=registry),
            patch.object(connection_workflow.st, "radio", return_value="SQL Server"),
            patch.object(connection_workflow.st, "button", return_value=True),
            patch.object(connection_workflow.st, "markdown"),
            patch.object(connection_workflow.st, "info"),
            patch.object(connection_workflow, "_render_connection_form", return_value={}),
            patch.object(connection_workflow, "_settings_signature", return_value="signature"),
            patch.object(connection_workflow, "_test_connection", side_effect=complete_connection),
            patch.object(connection_workflow.st, "rerun") as rerun,
        ):
            connection_workflow.render_connection_workflow(include_browse=False)

        rerun.assert_called_once_with()
        self.assertNotIn(connection_workflow.SUCCESS_RERUN_KEY, state)

    def test_success_reset_clears_form_and_transient_state_only(self) -> None:
        state = {
            "connections_sqlserver_host": "localhost",
            "connections_sqlserver_database": "catalog",
            "connections_sqlserver_password": "secret",
            connection_workflow.ACTIVE_CONNECTION_ID_KEY: "connection-1",
            connection_workflow.CONNECTOR_STATE_KEY: object(),
            connection_workflow.SIGNATURE_STATE_KEY: "signature",
            connection_workflow.ACTIVE_DATABASE_STATE_KEY: "catalog",
            connection_workflow.CONFIGURED_DATABASE_STATE_KEY: "catalog",
            connection_workflow.SCHEMAS_STATE_KEY: ["dbo"],
            connection_workflow.SCHEMAS_CONNECTION_KEY: "connection-1",
            connection_workflow.ACTIVE_SOURCE_STATE_KEY: "sqlserver",
            "unrelated_state": "keep",
        }

        with patch.object(connection_workflow.st, "session_state", state):
            connection_workflow._reset_connection_form_state("SQL Server")

        self.assertNotIn("connections_sqlserver_host", state)
        self.assertNotIn("connections_sqlserver_database", state)
        self.assertNotIn("connections_sqlserver_password", state)
        self.assertNotIn(connection_workflow.ACTIVE_CONNECTION_ID_KEY, state)
        self.assertNotIn(connection_workflow.CONNECTOR_STATE_KEY, state)
        self.assertNotIn(connection_workflow.SCHEMAS_STATE_KEY, state)
        self.assertEqual(state[connection_workflow.ACTIVE_SOURCE_STATE_KEY], "sqlserver")
        self.assertEqual(state["unrelated_state"], "keep")
        self.assertEqual(state[connection_workflow.STATUS_STATE_KEY], "not_configured")


if __name__ == "__main__":
    unittest.main()
