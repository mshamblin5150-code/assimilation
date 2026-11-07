# Chad’s practical lesson: let your drone retrieve the evidence

When your drone needs records from a repository, you should not have to become its file courier. Give it a clear investigation and ask it to use the access it actually has.

This lesson teaches one skill: directing a drone to collect reliable evidence before asking you or Matt for help. It builds on [the harness lesson](CHAD-HARNESS-ENGINEERING.md). You remain responsible for decisions; the drone does the permitted legwork.

## 1. Give it the source and a bounded job

Use Assimilation’s [PR #12](https://github.com/mshamblin5150-code/assimilation/pull/12) as a read-only exercise. You do not need to know the GitHub API commands. Give your drone the links and this instruction:

> Inspect Assimilation PR #12 directly using your available authorized read tools. Collect its full base and head commit SHAs, the diff for that pair, review 5724870011 including any inline comments, and the Issue #11 discussion. Also collect existing CI records for PRs #12 and #14, identifying the run, tested commit, platform, outcome, and skips.
>
> Keep the current code separate from the revision that was reviewed. Give me source links and identify anything missing. Existing records are enough: do not change the repository, rerun CI, install software, or change access. If something is inaccessible, retrieve the independent items you can and report the exact barrier before asking me or Matt to export it.

This gives the drone an outcome and boundaries. It does not prescribe commands or force you to retrieve the evidence first.

## 2. Check the report, not just its confidence

Expect a short inventory of what it retrieved and what remains missing. For each item, it should give a direct link and the relevant commit or run identity.

Ask these questions:

- **Which code did the review cover?** A review of an older head does not approve newer changes. “COMMENTED” is not “APPROVED.”
- **Did you read the complete discussion?** The drone should check additional pages and distinguish no comments from comments it could not retrieve.
- **What did CI actually run?** A successful summary does not prove every test ran. Skips, platform limits, and missing full logs should remain visible.
- **What did you inspect versus execute?** This exercise reads existing evidence. It does not run tests or qualify an installer.

If the report says only “everything looks good,” ask:

> Show me the evidence for that conclusion, including the exact revision and what remains untested.

## 3. Handle a real access problem without taking over the whole job

Your GitHub access and your drone’s access are not automatically identical. Being a contributor or collaborator does not supply its session with a signed-in connector, browser, or network route.

A useful blocker report sounds like this:

> I retrieved the diff, commit SHAs, review, and issue discussion. The full log for run [ID/link] requires sign-in in this session. Its public summary is available. I can continue comparing the review with the code; the remaining gap is that one log.

Then you can decide whether an authorized signed-in route or an export is appropriate. Ask for the smallest missing action, not a new setup project.

If it simply says “send me the files,” respond:

> Which original records did you try to read, using which available tool, and what exact result blocked you? Continue the independent reads you are permitted to make.

An actual access denial remains a boundary. Do not instruct the drone to evade it through another account or route. Missing tools, authentication requirements, network errors, and expired records are different problems; ask it to distinguish them rather than guess.

## 4. Use the real example to test the habit

On November 7, 2026, verification found PR #12’s diff, commit identities, [review 5724870011](https://github.com/mshamblin5150-code/assimilation/pull/12#pullrequestreview-5724870011), and [Issue #11’s discussion](https://github.com/mshamblin5150-code/assimilation/issues/11) publicly readable. The review concerned an earlier head and had no inline comments attached.
[Public CI summaries](https://github.com/mshamblin5150-code/assimilation/actions/runs/41530952383) were readable.
The web page required sign-in to view logs. The unauthenticated
[full-log API request](https://api.github.com/repos/mshamblin5150-code/assimilation/actions/runs/41530952383/logs)
returned HTTP 403, "Must have admin rights to Repository." Sign-in alone is not
proof that a session can retrieve that log.

Have your drone check the current records rather than copy those historical findings. GitHub records can change, and Actions logs and artifacts have
[retention limits](https://docs.github.com/en/organizations/managing-organization-settings/configuring-the-retention-period-for-github-actions-artifacts-and-logs-in-your-organization).

Finish by asking:

> What could you retrieve independently? What still needs my decision or access? What does this evidence prove, and what does it not prove?

You have completed the exercise when every requested item is either linked to its exact evidence or paired with a specific access gap, and you can explain the next step without collecting the entire packet yourself.

A ZIP is still useful for preserving a snapshot, sharing it with an offline reviewer, or filling a demonstrated access gap. It is an option, not the starting assumption.

**The Borg version: assimilate the available evidence; escalate the actual decision.**

