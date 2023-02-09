"""Test selecting an object store with user's preferred object store."""

import os
import string
from typing import (
    Any,
    Dict,
)

from galaxy.model import Dataset
from galaxy_test.base.populators import WorkflowPopulator
from ._base import BaseObjectStoreIntegrationTestCase

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))

DISTRIBUTED_OBJECT_STORE_CONFIG_TEMPLATE = string.Template(
    """<?xml version="1.0"?>
<object_store type="distributed" id="primary" order="0">
    <backends>
        <backend id="default" allow_selection="true" type="disk" weight="1" name="Default Store">
            <description>This is my description of the default store with *markdown*.</description>
            <files_dir path="${temp_directory}/files_default"/>
            <extra_dir type="temp" path="${temp_directory}/tmp_default"/>
            <extra_dir type="job_work" path="${temp_directory}/job_working_directory_default"/>
        </backend>
        <backend id="static" allow_selection="true" type="disk" weight="0" name="Static Storage">
            <files_dir path="${temp_directory}/files_static"/>
            <extra_dir type="temp" path="${temp_directory}/tmp_static"/>
            <extra_dir type="job_work" path="${temp_directory}/job_working_directory_static"/>
        </backend>
        <backend id="dynamic_ebs" allow_selection="true" type="disk" weight="0" name="Dynamic EBS">
            <quota source="ebs" />
            <files_dir path="${temp_directory}/files_dynamic_ebs"/>
            <extra_dir type="temp" path="${temp_directory}/tmp_dynamic_ebs"/>
            <extra_dir type="job_work" path="${temp_directory}/job_working_directory_dynamic_ebs"/>
        </backend>
        <backend id="dynamic_s3" type="disk" weight="0">
            <quota source="s3" />
            <files_dir path="${temp_directory}/files_dynamic_s3"/>
            <extra_dir type="temp" path="${temp_directory}/tmp_dynamic_s3"/>
            <extra_dir type="job_work" path="${temp_directory}/job_working_directory_dynamic_s3"/>
        </backend>
    </backends>
</object_store>
"""
)


TEST_WORKFLOW = """
class: GalaxyWorkflow
inputs:
  input1: data
outputs:
  wf_output_1:
    outputSource: second_cat/out_file1
steps:
  first_cat:
    tool_id: cat
    in:
      input1: input1
  second_cat:
    tool_id: cat
    in:
      input1: first_cat/out_file1
"""

TEST_WORKFLOW_TEST_DATA = """
input1:
  value: 1.fasta
  type: File
  name: fasta1
"""

TEST_WORKFLOW_MAPPED_COLLECTION_OUTPUT = """
class: GalaxyWorkflow
inputs:
  input1:
    type: data_collection_input
    collection_type: list
outputs:
  wf_output_1:
    outputSource: second_cat/out_file1
steps:
  first_cat:
    tool_id: cat
    in:
      input1: input1
  second_cat:
    tool_id: cat
    in:
      input1: first_cat/out_file1
"""


def assert_storage_name_is(storage_dict: Dict[str, Any], name: str):
    storage_name = storage_dict["name"]
    assert name == storage_name, f"Found incorrect storage name {storage_name}, expected {name} in {storage_dict}"


class TestObjectStoreSelectionWithPreferredObjectStoresIntegration(BaseObjectStoreIntegrationTestCase):
    # populated by config_object_store
    files_default_path: str
    files_static_path: str
    files_dynamic_path: str
    files_dynamic_ebs_path: str
    files_dynamic_s3_path: str

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls._configure_object_store(DISTRIBUTED_OBJECT_STORE_CONFIG_TEMPLATE, config)
        config["object_store_store_by"] = "uuid"
        config["outputs_to_working_directory"] = True

    def setUp(self):
        super().setUp()
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)

    def test_setting_unselectable_object_store_id_not_allowed(self):
        response = self.dataset_populator.update_user_raw({"preferred_object_store_id": "dynamic_s3"})
        assert response.status_code == 400

    def test_index_query(self):
        selectable_object_stores_response = self._get("object_store?selectable=true")
        selectable_object_stores_response.raise_for_status()
        selectable_object_stores = selectable_object_stores_response.json()
        selectable_object_store_ids = [s["object_store_id"] for s in selectable_object_stores]
        assert "default" in selectable_object_store_ids
        assert "static" in selectable_object_store_ids
        assert "dynamic_s3" not in selectable_object_store_ids

    def test_objectstore_selection(self):

        with self.dataset_populator.test_history() as history_id:

            def _create_hda_get_storage_info():
                hda1 = self.dataset_populator.new_dataset(history_id, content="1 2 3")
                self.dataset_populator.wait_for_history(history_id)
                return self._storage_info(hda1), hda1

            def _run_tool(tool_id, inputs, preferred_object_store_id=None):
                response = self.dataset_populator.run_tool(
                    tool_id,
                    inputs,
                    history_id,
                    preferred_object_store_id=preferred_object_store_id,
                )
                self.dataset_populator.wait_for_history(history_id)
                return response

            user_properties = self.dataset_populator.update_user({"preferred_object_store_id": "static"})
            assert user_properties["preferred_object_store_id"] == "static"

            storage_info, hda1 = _create_hda_get_storage_info()
            assert_storage_name_is(storage_info, "Static Storage")

            user_properties = self.dataset_populator.update_user({"preferred_object_store_id": None})

            storage_info, _ = _create_hda_get_storage_info()
            assert_storage_name_is(storage_info, "Default Store")

            self.dataset_populator.update_history(history_id, {"preferred_object_store_id": "static"})
            storage_info, _ = _create_hda_get_storage_info()
            assert_storage_name_is(storage_info, "Static Storage")

            hda1_input = {"src": "hda", "id": hda1["id"]}
            response = _run_tool("multi_data_param", {"f1": hda1_input, "f2": hda1_input})
            storage_info = self._storage_info_for_job_output(response)
            assert_storage_name_is(storage_info, "Static Storage")

            hda1_input = {"src": "hda", "id": hda1["id"]}
            response = _run_tool(
                "multi_data_param", {"f1": hda1_input, "f2": hda1_input}, preferred_object_store_id="default"
            )
            storage_info = self._storage_info_for_job_output(response)
            assert_storage_name_is(storage_info, "Default Store")

            # reset preferred object store...
            self.dataset_populator.update_user({"preferred_object_store_id": None})

    def test_workflow_objectstore_selection(self):

        with self.dataset_populator.test_history() as history_id:
            output_dict, intermediate_dict = self._run_workflow_get_output_storage_info_dicts(history_id)
            assert_storage_name_is(output_dict, "Default Store")
            assert_storage_name_is(intermediate_dict, "Default Store")

            output_dict, intermediate_dict = self._run_workflow_get_output_storage_info_dicts(
                history_id, {"preferred_object_store_id": "static"}
            )
            assert_storage_name_is(output_dict, "Static Storage")
            assert_storage_name_is(intermediate_dict, "Static Storage")

            output_dict, intermediate_dict = self._run_workflow_get_output_storage_info_dicts(
                history_id,
                {
                    "preferred_outputs_object_store_id": "static",
                    "preferred_intermediate_object_store_id": "dynamic_ebs",
                },
            )
            assert_storage_name_is(output_dict, "Static Storage")
            assert_storage_name_is(intermediate_dict, "Dynamic EBS")

    def _run_workflow_get_output_storage_info_dicts(self, history_id, extra_invocation_kwds=None):
        wf_run = self.workflow_populator.run_workflow(
            TEST_WORKFLOW,
            test_data=TEST_WORKFLOW_TEST_DATA,
            history_id=history_id,
            extra_invocation_kwds=extra_invocation_kwds,
        )
        jobs = wf_run.jobs_for_tool("cat")
        print(jobs)
        assert len(jobs) == 2
        output_cat = self.dataset_populator.get_job_details(jobs[0]["id"], full=True).json()
        intermediate_cat = self.dataset_populator.get_job_details(jobs[1]["id"], full=True).json()
        output_info = self._storage_info_for_job_output(output_cat)
        intermediate_info = self._storage_info_for_job_output(intermediate_cat)
        return output_info, intermediate_info

    def _storage_info_for_job_output(self, job_dict):
        outputs = job_dict["outputs"]  # could be a list or dictionary depending on source
        try:
            output = outputs[0]
        except KeyError:
            output = list(outputs.values())[0]
        storage_info = self._storage_info(output)
        return storage_info

    def _storage_info(self, hda):
        return self.dataset_populator.dataset_storage_info(hda["id"])

    @property
    def _latest_dataset(self):
        latest_dataset = self._app.model.session.query(Dataset).order_by(Dataset.table.c.id.desc()).first()
        return latest_dataset
