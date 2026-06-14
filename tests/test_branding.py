from magical_girl_glow_down.branding import (
    APP_DISPLAY_NAME,
    APP_ID,
    APP_NAME,
    CLI_NAME,
    DISTRIBUTION_NAME,
    icon_path,
)


def test_branding_uses_final_product_identity() -> None:
    assert APP_NAME == "MagicalGirlGlowDown"
    assert APP_DISPLAY_NAME == "魔法少女·静谧霓虹"
    assert APP_ID == "LingMoe404.MagicalGirlGlowDown"
    assert DISTRIBUTION_NAME == "magical-girl-glow-down"
    assert CLI_NAME == "magical-girl-glow-down"


def test_packaged_logo_exists() -> None:
    assert icon_path().is_file()
