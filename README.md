# JRNL (journal)

***Work in progress***

Fork from https://github.com/jrnl-org/jrnl
... in the meanwhile a short comment is that the current ambition for this project make this so that it'd be simpler to use with certain shortcuts (you'll see) .. but also more focused around keep track of activities and how long time spent on them for future summarization.

## Main changes

- Automatically add tag for identifying entries as tasks using following pattern `@tag:<major>.<minor>` if missing
  - ***Example***: Foo Bar `@task:1.0` - tasks where minor is `0` is the main task
  - Linked tasks will have inceremented minor such as `@task2.1` associated with task `2` meant to easier group tasks together.
  - If e.g. `@task:2.0` added in title and already exists will automatically make this as incremented subtask `@task:2.1`
- Tags used to idenfity TaskStatus following the pattern `@<status>:YYYY-mm-dd`
  - Status currently available: `todo`, `ongoing` and `completed`
  - If no status supplied at creation of entry, `completed:<todays date>` will be added
