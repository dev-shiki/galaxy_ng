import sys

# Add project root to path if needed
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "galaxy_ng.settings")
from django.conf import settingsimport pytest
import os
import sys
import pytest
from django.core.management import call_command
from galaxy_ng.app.models import CollectionRemote
from galaxy_ng.app.models import AnsibleRepository
from galaxy_ng.app.models import CollectionVersion
from galaxy_ng.app.management.commands.sync_galaxy_collections import Command
from galaxy_ng.app.utils.galaxy import upstream_collection_iterator
from galaxy_ng.app.utils.legacy import process_namespace
from pulp_ansible.app.models import Collection
from pulp_ansible.app.models import CollectionVersion as PulpCollectionVersion
from pulp_ansible.app.models import CollectionRemote as PulpCollectionRemote
from pulp_ansible.app.models import AnsibleRepository as PulpAnsibleRepository
from pulp_ansible.app.models import Task
from pulpcore.plugin.constants import TASK_STATES
from pulpcore.plugin.constants import TASK_FINAL_STATES
from pulpcore.plugin.tasking import dispatch
from pulpcore.plugin.tasking import Task as PulpTask
from pulpcore.plugin.tasking import TaskRun
from pulpcore.plugin.tasking import TaskState
from pulpcore.plugin.tasking import TaskStatus
from pulpcore.plugin.tasking import TaskResult
from pulpcore.plugin.tasking import TaskError
from pulpcore.plugin.tasking import TaskReport
from pulpcore.plugin.tasking import TaskReportError
from pulpcore.plugin.tasking import TaskReportSuccess
from pulpcore.plugin.tasking import TaskReportWarning
from pulpcore.plugin.tasking import TaskReportInfo
from pulpcore.plugin.tasking import TaskReportDebug
from pulpcore.plugin.tasking import TaskReportCritical
from pulpcore.plugin.tasking import TaskReportError as PulpTaskReportError
from pulpcore.plugin.tasking import TaskReportSuccess as PulpTaskReportSuccess
from pulpcore.plugin.tasking import TaskReportWarning as PulpTaskReportWarning
from pulpcore.plugin.tasking import TaskReportInfo as PulpTaskReportInfo
from pulpcore.plugin.tasking import TaskReportDebug as PulpTaskReportDebug
from pulpcore.plugin.tasking import TaskReportCritical as PulpTaskReportCritical
from pulpcore.plugin.tasking import TaskReport as PulpTaskReport
from pulpcore.plugin.tasking import TaskRun as PulpTaskRun
from pulpcore.plugin.tasking import TaskState as PulpTaskState
from pulpcore.plugin.tasking import TaskStatus as PulpTaskStatus
from pulpcore.plugin.tasking import TaskResult as PulpTaskResult
from pulpcore.plugin.tasking import TaskError as PulpTaskError
from pulpcore.plugin.tasking import TaskReportError as PulpTaskReportError
from pulpcore.plugin.tasking import TaskReportSuccess as PulpTaskReportSuccess
from pulpcore.plugin.tasking import TaskReportWarning as PulpTaskReportWarning
from pulpcore.plugin.tasking import TaskReportInfo as PulpTaskReportInfo
from pulpcore.plugin.tasking import TaskReportDebug as PulpTaskReportDebug
from pulpcore.plugin.tasking import TaskReportCritical as PulpTaskReportCritical
from pulpcore.plugin.tasking import TaskReport as PulpTaskReport
from pulpcore.plugin.tasking import TaskRun as PulpTaskRun
from pulpcore.plugin.tasking import TaskState as PulpTaskState
from pulpcore.plugin.tasking import TaskStatus as PulpTaskStatus
from pulpcore.plugin.tasking import TaskResult as PulpTaskResult
from pulpcore.plugin.tasking import TaskError as PulpTaskError
from pulpcore.plugin.tasking import TaskReportError as PulpTaskReportError
from pulpcore.plugin.tasking import TaskReportSuccess as PulpTaskReportSuccess
from pulpcore.plugin.tasking import TaskReportWarning as PulpTaskReportWarning
from pulpcore.plugin.tasking import TaskReportInfo as PulpTaskReportInfo
from pulpcore.plugin.tasking import TaskReportDebug as PulpTaskReportDebug
from pulpcore.plugin.tasking import TaskReportCritical as PulpTaskReportCritical
from pulpcore.plugin.tasking import TaskReport as PulpTaskReport
from pulpcore.plugin.tasking import TaskRun as PulpTaskRun
from pulpcore.plugin.tasking import TaskState as PulpTaskState
from pulpcore.plugin.tasking import TaskStatus as PulpTaskStatus
from pulpcore.plugin.tasking import TaskResult as PulpTaskResult
from pulpcore.plugin.tasking import TaskError as PulpTaskError
from pulpcore.plugin.tasking import TaskReportError as PulpTaskReportError
from pulpcore.plugin.tasking import Task as PulpTask
from pulpcore.tasking import TaskRun as PulpTaskRun
from pulpcore.tasking import TaskState as PulpTaskState
from pulpcore.tasking import TaskStatus as PulpTaskStatus
from pulpcore.tasking import TaskResult as PulpTaskResult
from pulpcore.tasking import TaskError as PulpTaskError
from pulpcore.tasking import TaskReportError as PulpTaskReportError
from pulpcore.tasking import TaskReportSuccess as PulpTaskReportSuccess
from pulpcore.tasking import TaskReportWarning as PulpTaskReportWarning
from pulpcore.tasking import TaskReportInfo as PulpTaskReportInfo
from pulpcore.tasking import TaskReportDebug as PulpTaskReportDebug
from pulpcore.tasking import TaskReportCritical as PulpTaskReportCritical
from pulpcore.tasking import TaskReport as PulpTaskReport
from pulpcore.tasking import TaskRun as PulpTaskRun
from pulpcore.tasking import TaskState as PulpTaskState
from pulpcore.tasking import TaskStatus as PulpTaskStatus
from pulpcore.tasking import TaskResult as PulpTaskResult
from pulpcore.tasking import TaskError as PulpTaskError
from pulpcore.tasking import TaskReportError as PulpTaskReportError
from pulpcore.tasking import TaskReportSuccess as PulpTaskReportSuccess
from pulpcore.tasking import TaskReportWarning as PulpTaskReportWarning
from pulpcore.tasking import TaskReportInfo as PulpTaskReportInfo
from pulpcore.tasking import TaskReportDebug as PulpTaskReportDebug
from pulpcore.tasking import TaskReportCritical as PulpTaskReportCritical
from pulpcore.tasking import TaskReport as PulpTaskReport
from pulpcore.tasking import TaskRun as PulpTaskRun
from pulpcore.tasking import TaskState as PulpTaskState
from pulpcore.tasking import TaskStatus as PulpTaskStatus
from pulpcore.tasking import TaskResult as PulpTaskResult
from pulpcore.tasking import TaskError as PulpTaskError
from pulpcore.tasking import TaskReportError as PulpTaskReportError
from pulpcore.tasking import TaskReportSuccess as PulpTaskReportSuccess
from pulpcore.tasking import TaskReportWarning as PulpTaskReportWarning
from pulpcore.tasking import TaskReportInfo as PulpTaskReportInfo
from pulpcore.tasking import TaskReportDebug as PulpTaskReport
from pulpcore.tasking import TaskRun as PulpTaskRun
from pulpcore.tasking import TaskState as PulpTaskState
from pulpcore.tasking import TaskStatus as PulpTaskStatus
from pulpcore.tasking import TaskResult as PulpTaskResult
from pulpcore.tasking import TaskError as PulpTaskError
from pulpcore.tasking import TaskReportError as PulpTaskReportError
from pulpcore.tasking import TaskReportSuccess as PulpTaskReportSuccess
from pulpcore.tasking import TaskReportWarning as PulpTaskReportWarning
from pulpcore.tasking import TaskReportInfo as PulpTaskReportInfo
from pulpcore.tasking import TaskReportDebug as PulpTaskReportDebug
from pulpcore.tasking import TaskReportCritical as PulpTaskReportCritical
from pulpcore.tasking import TaskReport as PulpTaskReport
from pulpcore.tasking import TaskRun as PulpTaskRun
from pulpcore.tasking import TaskState as PulpTaskState
from pulpcore.tasking import TaskStatus as PulpTaskStatus
from pulpcore.tasking import TaskResult as PulpTaskResult
from pulpcore.tasking import TaskError as PulpTaskError
from pulpcore.tasking import TaskReportError as PulpTaskReportError
from pulpcore.tasking import TaskReportSuccess as PulpTaskReportSuccess
from pulpcore.tasking import TaskReportWarning as PulpTaskReportWarning
from pulpcore.tasking import TaskReportInfo as PulpTaskReportInfo
from pulpcore.tasking import TaskReportDebug as PulpTaskReportDebug
from pulpcore.tasking import TaskReportCritical as PulpTaskReportCritical
from pulpcore.tasking import TaskReport as PulpTaskReport
from pulpcore.tasking import TaskRun as PulpTaskRun
from pulpcore.tasking import TaskState as PulpTaskState
from pulpcore.tasking import TaskStatus as PulpTaskStatus
from pulpcore.tasking import TaskResult as PulpTaskResult
from pulpcore.tasking import TaskError as PulpTaskError
from pulpcore.tasking import TaskReportError as PulpTaskReportError
from pulpcore.tasking import TaskReportSuccess as PulpTaskReportSuccess
from pulpcore.tasking import TaskReportWarning as PulpTaskReportWarning
from pulpcore.tasking import TaskReportInfo as PulpTaskReportInfo
from pulpcore.tasking import TaskReportDebug as PulpTaskReportDebug
from pulpcore.tasking import TaskReportCritical as PulpTaskReportCritical
from pulpcore.tasking import TaskReport as PulpTaskReport
from pulpcore.tasking import TaskRun as PulpTaskRun
from pulpcore.tasking import TaskState as PulpTaskState
from pulpcore.tasking import TaskStatus as PulpTaskStatus
from pulpcore.tasking import TaskResult as PulpTaskResult
from pulpcore.tasking import TaskError as PulpTaskError
from pulpcore.tasking import TaskReportError as PulpTaskReportError
from pulpcore.tasking import TaskReportSuccess as PulpTaskReportSuccess
from pulpcore.tasking import TaskReportWarning as PulpTaskReportWarning
from pulpcore.tasking import TaskReportInfo as PulpTaskReportInfo
from pulpcore.tasking import TaskReportDebug as PulpTaskReportDebug
from pulpcore.tasking import TaskReportCritical as PulpTaskReportCritical
from pulpcore.tasking import TaskReport as PulpTaskReport
from pulpcore.tasking import TaskRun as PulpTaskRun
from pulpcore.tasking import TaskState as PulpTaskState
from pulpcore.tasking import TaskStatus as PulpTaskStatus
from pulpcore.tasking import TaskResult as PulpTaskResult
from pulpcore.tasking import TaskError as PulpTaskError
from pulpcore.tasking import TaskReportError as PulpTaskReportError
from pulpcore.tasking import TaskReportSuccess as PulpTaskReportSuccess
from pulpcore.tasking import TaskReportWarning as PulpTaskReportWarning
from pulpcore.tasking import TaskReportInfo as PulpTaskReportInfo
from pulpcore.tasking import TaskReportDebug as PulpTaskReportDebug
from pulpcore.tasking import TaskReportCritical as PulpTaskReportCritical
from pulpcore.tasking import TaskReport as PulpTaskReport
from pulpcore.tasking import TaskRun as PulpTaskRun
from pulpcore.tasking import TaskState as PulpTaskState
from pulpcore.tasking import TaskStatus as PulpTaskStatus
from pulpcore.tasking import TaskResult as PulpTaskResult
from pulpcore.tasking import TaskError as PulpTaskError
from pulpcore.tasking import TaskReportError as PulpTaskReportError
from pulpcore.tasking import TaskReportSuccess as PulpTaskReportSuccess
from pulpcore.tasking import TaskReportWarning as PulpTaskReportWarning
