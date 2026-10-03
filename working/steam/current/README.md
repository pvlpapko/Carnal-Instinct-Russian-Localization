# Steam current working area

All active Steam tasks live below this directory regardless of the currently installed Steam build.

Each substantial task should create:

`working/steam/current/<task>/AUDIT_STATE.json`

The task state records the verified source identity used for that checkpoint. If Steam updates, the workspace path remains stable and affected compatibility is revalidated instead of renaming the task directory.
