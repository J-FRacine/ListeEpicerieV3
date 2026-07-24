from pathlib import Path

from nicegui import app, ui


PWA_HEAD = r"""
<link rel="manifest" href="/manifest.webmanifest">
<link rel="icon" type="image/png" sizes="64x64" href="/assets/favicon-64.png">
<link rel="apple-touch-icon" sizes="180x180" href="/assets/apple-touch-icon.png">
<meta name="theme-color" content="#173553">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="JF Apps">

<script>
(() => {
    window.jfDeferredInstallPrompt = null;

    window.addEventListener(
        'beforeinstallprompt',
        (event) => {
            event.preventDefault();
            window.jfDeferredInstallPrompt = event;
        },
    );

    window.addEventListener(
        'appinstalled',
        () => {
            window.jfDeferredInstallPrompt = null;
        },
    );

    window.installJFApps = async () => {
        const isStandalone =
            window.matchMedia(
                '(display-mode: standalone)'
            ).matches
            || window.navigator.standalone === true;

        if (isStandalone) {
            return 'already';
        }

        if (window.jfDeferredInstallPrompt) {
            const promptEvent =
                window.jfDeferredInstallPrompt;

            promptEvent.prompt();

            const choice =
                await promptEvent.userChoice;

            window.jfDeferredInstallPrompt = null;

            return choice.outcome;
        }

        const isIOS =
            /iphone|ipad|ipod/i.test(
                window.navigator.userAgent
            );

        return isIOS ? 'ios' : 'menu';
    };

    if ('serviceWorker' in navigator) {
        window.addEventListener(
            'load',
            () => {
                navigator.serviceWorker
                    .register(
                        '/service-worker.js',
                        {scope: '/'},
                    )
                    .catch((error) => {
                        console.error(
                            'Échec de l’enregistrement PWA :',
                            error,
                        );
                    });
            },
        );
    }
})();
</script>
"""


def configure_pwa(
    base_dir: Path,
) -> None:
    resources = {
        "/manifest.webmanifest": (
            base_dir
            / "manifest.webmanifest",
            300,
        ),
        "/service-worker.js": (
            base_dir
            / "service-worker.js",
            0,
        ),
        "/offline.html": (
            base_dir
            / "offline.html",
            300,
        ),
        "/assets/pwa-icon-192.png": (
            base_dir
            / "pwa-icon-192.png",
            86400,
        ),
        "/assets/pwa-icon-512.png": (
            base_dir
            / "pwa-icon-512.png",
            86400,
        ),
        "/assets/pwa-icon-maskable-512.png": (
            base_dir
            / "pwa-icon-maskable-512.png",
            86400,
        ),
        "/assets/apple-touch-icon.png": (
            base_dir
            / "apple-touch-icon.png",
            86400,
        ),
        "/assets/favicon-64.png": (
            base_dir
            / "favicon-64.png",
            86400,
        ),
    }

    missing = [
        str(local_file)
        for (
            local_file,
            _
        ) in resources.values()
        if not local_file.exists()
    ]

    if missing:
        raise RuntimeError(
            "Fichiers PWA manquants : "
            + ", ".join(missing)
        )

    for (
        url_path,
        (
            local_file,
            max_cache_age,
        ),
    ) in resources.items():
        app.add_static_file(
            url_path=url_path,
            local_file=str(local_file),
            max_cache_age=max_cache_age,
        )

    ui.add_head_html(
        PWA_HEAD,
        shared=True,
    )


async def request_pwa_install() -> None:
    try:
        result = await ui.run_javascript(
            """
            if (
                typeof window.installJFApps
                !== 'function'
            ) {
                return 'unavailable';
            }

            return await window.installJFApps();
            """,
            timeout=30.0,
        )
    except Exception:
        result = "unavailable"

    messages = {
        "accepted": (
            "Installation lancée. "
            "JF Apps apparaîtra sur "
            "l’écran d’accueil."
        ),
        "dismissed": (
            "Installation annulée. "
            "Vous pourrez réessayer "
            "plus tard."
        ),
        "already": (
            "JF Apps est déjà ouverte "
            "comme application installée."
        ),
        "ios": (
            "Sur iPhone ou iPad : ouvrez "
            "le menu Partager de Safari, "
            "puis choisissez "
            "« Sur l’écran d’accueil »."
        ),
        "menu": (
            "Ouvrez le menu du navigateur, "
            "puis choisissez "
            "« Installer l’application » "
            "ou « Ajouter à "
            "l’écran d’accueil »."
        ),
        "unavailable": (
            "L’installation automatique "
            "n’est pas disponible dans ce "
            "navigateur. Utilisez son menu "
            "pour ajouter JF Apps à "
            "l’écran d’accueil."
        ),
    }

    ui.notify(
        messages.get(
            result,
            messages["unavailable"],
        ),
        type=(
            "positive"
            if result == "accepted"
            else "info"
        ),
        timeout=9000,
        close_button=True,
    )
