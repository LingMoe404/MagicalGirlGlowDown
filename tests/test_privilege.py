from magical_girl_glow_down.privilege import requires_elevation


def test_tray_and_gigabyte_write_commands_require_elevation() -> None:
    assert requires_elevation(
        simulate=False,
        gigabyte_probe=False,
        install_autostart=False,
        remove_autostart=False,
    )
    assert requires_elevation(
        simulate=False,
        gigabyte_probe=False,
        gigabyte_snapshot=True,
        install_autostart=False,
        remove_autostart=False,
    )


def test_read_only_commands_do_not_require_elevation() -> None:
    assert not requires_elevation(
        simulate=True,
        gigabyte_probe=False,
        install_autostart=False,
        remove_autostart=False,
    )
    assert not requires_elevation(
        simulate=False,
        gigabyte_probe=True,
        install_autostart=False,
        remove_autostart=False,
    )
    assert requires_elevation(
        simulate=False,
        gigabyte_probe=False,
        install_autostart=True,
        remove_autostart=False,
    )
    assert requires_elevation(
        simulate=False,
        gigabyte_probe=False,
        install_autostart=False,
        remove_autostart=True,
    )
