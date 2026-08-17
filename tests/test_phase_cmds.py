def test_phase_cmds_is_dict_of_nonempty_str_lists(ss):
    assert isinstance(ss.PHASE_CMDS, dict)
    assert ss.PHASE_CMDS
    for phase, args in ss.PHASE_CMDS.items():
        assert isinstance(phase, str) and phase
        assert isinstance(args, list) and args
        assert all(isinstance(a, str) and a for a in args)


def test_phase_cmds_known_phases_present(ss):
    expected = {
        "precheck-install", "install", "postcheck-install",
        "enable-daemon", "nodeid-define",
        "precheck-deploy", "deploy", "postcheck-deploy",
        "upgrade-precheck", "upgrade-run", "upgrade-postcheck", "upgrade-showversions",
    }
    assert expected <= ss.PHASE_CMDS.keys()


def test_upgrade_phases_use_positional_subcommands_not_flags(ss):
    # Regression guard: `spectrumscale upgrade` takes a positional
    # subcommand ({config,run,precheck,postcheck,showversions}), not
    # flags like --precheck/--upgrade-protocols — the app's Upgrade page
    # generated exactly that wrong syntax before it was corrected.
    for phase in ("upgrade-precheck", "upgrade-run", "upgrade-postcheck", "upgrade-showversions"):
        args = ss.PHASE_CMDS[phase]
        assert args[0] == "upgrade"
        assert not any(a.startswith("-") for a in args), f"{phase} should have no flags: {args}"


def test_skip_ssh_phases_derived_from_install_and_deploy_only(ss):
    for phase in ss._SKIP_SSH_PHASES:
        assert "install" in phase or "deploy" in phase
    for phase in ss.PHASE_CMDS:
        if "install" in phase or "deploy" in phase:
            assert phase in ss._SKIP_SSH_PHASES
    # Upgrade phases must never get --skip ssh appended.
    for phase in ("upgrade-precheck", "upgrade-run", "upgrade-postcheck", "upgrade-showversions"):
        assert phase not in ss._SKIP_SSH_PHASES
