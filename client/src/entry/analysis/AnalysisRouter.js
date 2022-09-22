/** define the 'Analyze Data'/analysis/main/home page for Galaxy
 *  * has a masthead
 *  * a left tool menu to allow the user to load tools in the center panel
 *  * a right history menu that shows the user's current data
 *  * a center panel
 *  Both panels (generally) persist while the center panel shows any
 *  UI needed for the current step of an analysis, like:
 *      * tool forms to set tool parameters,
 *      * tables showing the contents of datasets
 *      * etc.
 */

import _ from "underscore";
import { getGalaxyInstance } from "app";
import { getAppRoot } from "onload";
import decodeUriComponent from "decode-uri-component";
import Router from "layout/router";
import ToolForm from "components/Tool/ToolForm";
import WorkflowRun from "components/Workflow/Run/WorkflowRun.vue";
import QueryStringParsing from "utils/query-string-parsing";

import { newUserDict } from "../../../../static/plugins/welcome_page/new_user/dist/static/topics/index";

/** Routes */
export const getAnalysisRouter = (Galaxy) => {
    return Router.extend({
        routes: {
            "(/)(#)(_=_)": "home",
            "(/)root*": "home",
            // a bunch of routes removed...
        },

        /** A bunch of routes removed...  */
        home: function (params) {
            // TODO: to router, remove Globals
            // load a tool by id (tool_id) or rerun a previous tool execution (job_id)
            if (params.tool_id || params.job_id) {
                if (params.tool_id === "upload1") {
                    this.page.toolPanel.upload.show();
                    this._loadCenterIframe("welcome");
                } else {

                    // *** BEGIN ADDED ***
                    //
		            // Handle rerun of InteractiveClientTool
                    if (params.job_id && params.id) {
                        const url = `${getAppRoot()}api/jobs/${params.job_id}/build_for_rerun`;
                        const {data} = await axios.get(url)

                        if (data.model_class === "InteractiveClientTool") {
                            const rerun_url = `tool_runner/rerun?id=${params.id}`
                            this._loadCenterIframe(rerun_url)
                            return
                        }
                    }
                    //
                    // *** END ADDED ***

                    this._loadToolForm(params);
                }
            } else {
                // show the workflow run form
                if (params.workflow_id) {
                    this._loadWorkflow();
                    // load the center iframe with controller.action: galaxy.org/?m_c=history&m_a=list -> history/list
                } else if (params.m_c) {
                    this._loadCenterIframe(`${params.m_c}/${params.m_a}`);
                    // show the workflow run form
                } else {
                    this._loadCenterIframe("welcome");
                }
            }
        },

        mountWelcome: async function () {
            const propsData = {
                newUserDict,
            };
            return import(/* webpackChunkName: "NewUserWelcome" */ "components/NewUserWelcome/NewUserWelcome.vue").then(
                (module) => {
                    this._display_vue_helper(module.default, propsData);
                }
            );
        },

        /** load the center panel with a tool form described by the given params obj */
        _loadToolForm: function (params) {
            //TODO: load tool form code async
            if (params.tool_id) {
                params.id = decodeUriComponent(params.tool_id);
            }
            if (params.version) {
                params.version = decodeUriComponent(params.version);
            }
            this._display_vue_helper(ToolForm, params);
        },

        /** load the center panel iframe using the given url */
        _loadCenterIframe: function (url, root) {
            root = root || getAppRoot();
            url = root + url;
            this.page.$("#galaxy_main").prop("src", url);
        },

        /** load workflow by its url in run mode */
        _loadWorkflow: function () {
            const workflowId = QueryStringParsing.get("id");
            const Galaxy = getGalaxyInstance();
            let preferSimpleForm = Galaxy.config.simplified_workflow_run_ui == "prefer";
            const preferSimpleFormOverride = QueryStringParsing.get("simplified_workflow_run_ui");
            if (preferSimpleFormOverride == "prefer") {
                preferSimpleForm = true;
            }
            const simpleFormTargetHistory = Galaxy.config.simplified_workflow_run_ui_target_history;
            const simpleFormUseJobCache = Galaxy.config.simplified_workflow_run_ui_job_cache == "on";
            const props = {
                workflowId,
                preferSimpleForm,
                simpleFormTargetHistory,
                simpleFormUseJobCache,
            };
            this._display_vue_helper(WorkflowRun, props, "workflow");
        },
    });
};
