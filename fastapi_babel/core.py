from __future__ import annotations

import re
from gettext import gettext, pgettext, translation, NullTranslations
from subprocess import run
from typing import Callable, Optional
from fastapi import Request

from fastapi import Request
from fastapi.templating import Jinja2Templates
from pathlib import Path

from .helpers import check_click_import, check_jinja_import
from .properties import RootConfigs
from .exceptions import BabelProxyError
from contextvars import ContextVar


class Babel:

    instance: Optional[Babel] = None  # Singleton used by Babel CLI

    def __init__(self, configs: RootConfigs) -> None:
        """
        `Babel` is manager for babel localization
            and i18n tools like gettext, translation, ...

        Args:
            configs (RootConfigs): Babel configs for using.
        """
        self.config: RootConfigs = configs
        self.__locale: str = self.config.BABEL_DEFAULT_LOCALE
        self.__default_locale: str = self.config.BABEL_DEFAULT_LOCALE
        self.__domain: str = self.config.BABEL_DOMAIN.split(".")[0]

    @property
    def domain(self) -> str:
        return self.__domain

    @property
    def default_locale(self) -> str:
        return self.__default_locale

    @property
    def locale(self) -> str:
        return self.__locale

    @locale.setter
    def locale(self, value: str) -> None:
        self.__locale = value

    def get_translation(self) -> NullTranslations | None:
        if self.default_locale != self.locale:
            gt = translation(
                self.domain,
                self.config.BABEL_TRANSLATION_DIRECTORY,
                [self.locale],
            )
            gt.install()
            return gt

    @property
    def gettext(self) -> Callable[[str], str]:
        gt = self.get_translation()
        if gt is not None:
            return gt.gettext
        return gettext


    @property
    def pgettext(self) -> Callable[[str, str], str]:
        gt = self.get_translation()
        if gt is not None:
            return gt.pgettext
        return pgettext


    def install_jinja(self, templates: Jinja2Templates) -> None:
        """
        `Babel.install_jinja` install gettext to jinja2 environment
            to access `_` in whole
            the jinja templates and let it to pybabel for
            extracting included messages throughout the templates.

        Args:
            templates (Jinja2Templates): Starlette Jinja2Templates object.
        """
        check_jinja_import()
        from jinja2 import Environment

        self.env: Environment = templates.env
        globals: dict = self.env.globals
        globals.update({"_": _})

    def run_cli(self):
        """installs cli's for using pybabel commands easily by specified
        configs from `BabelConfigs`.
        """
        check_click_import()
        babel_cli = BabelCli(self)
        babel_cli.run()


class __LazyText:
    def __init__(self, message) -> None:
        self.message = message

    def __repr__(self) -> str:
        return _(self.message)


def make_gettext(request: Request) -> Callable[[str], str]:
    """translate the message and retrieve message from .PO and .MO depends on
    `Babel.locale` locale.

    Args:
        message (str): message content

    Returns:
        str: transalted message.
    """

    def translate(message: str) -> str:
        # Get Babel instance from request or fallback to the CLI instance (when defined)
        babel = require_babel_in_request(request)
        return babel.gettext(message)

    return translate


_context_var: ContextVar[Callable[[str], str]] = ContextVar("gettext")
_context_var_pgettext: ContextVar[Callable[[str, str], str]] = ContextVar("pgettext")


def _(message: str) -> str:
    gettext = _context_var.get()
    return gettext(message)

def _pgettext(context: str, message: str) -> str:
    return _context_var_pgettext.get()(context, message)


lazy_gettext = __LazyText


class BabelCli:
    __module_name__ = "pybabel"

    def __init__(self, babel: Babel) -> None:
        """Babel cli manager to facilitate using pybabel commands by specified congigs
        fron `BabelConfigs`.

        Args:
            babel (Babel): `Babel` instance
        """
        self.babel = babel

    def extract(self, watch_dir: str) -> None:
        """extract all messages that annotated using gettext/_
        in the specified directory.

        for first time will create messages.pot file into the root
        directory.

        Args:
            watch_dir (str): directory to extract messages.
        """
        run(
            [
                BabelCli.__module_name__,
                "extract",
                "-F",
                self.babel.config.BABEL_CONFIG_FILE,
                "-o",
                self.babel.config.BABEL_MESSAGE_POT_FILE,
                watch_dir,
            ]
        )

    def init(self, lang: Optional[str] = None) -> None:
        """Initialized lacale directory for first time.
        if there is already exists the directory, notice that your
        all comiled and initialized messages will remove, in this
        condition has better to use `Babel.update` method.

        Args:
            lang (str): locale directory name and path
        """
        run(
            [
                BabelCli.__module_name__,
                "init",
                "-i",
                self.babel.config.BABEL_MESSAGE_POT_FILE,
                "-d",
                self.babel.config.BABEL_TRANSLATION_DIRECTORY,
                "-l",
                lang or self.babel.config.BABEL_DEFAULT_LOCALE,
            ]
        )

    def update(self, watch_dir: Optional[str] = None) -> None:
        """update the extracted messages after init command/initialized directory
        , Default is `./lang`"

        Args:
            watch_dir (str): locale directory name and path
        """
        run(
            [
                BabelCli.__module_name__,
                "update",
                "-i",
                self.babel.config.BABEL_MESSAGE_POT_FILE,
                "-d",
                watch_dir or self.babel.config.BABEL_TRANSLATION_DIRECTORY,
            ]
        )

    def compile(self):
        """
        compile all messages from translation directory in .PO to .MO file and is
        a binnary text file.
        """
        run(
            [
                BabelCli.__module_name__,
                "compile",
                "-d",
                self.babel.config.BABEL_TRANSLATION_DIRECTORY,
            ]
        )

    def run(self):
        from click import echo, group, option

        @group(
            "cmd",
            help="""
            First Step to extracting messages:\n

                1- extract -d/--dir {watch_dir}\n
                2- init -l/--lang {lang}\n
                3- add your custome translation to your lang `.po` file for example FA dir {./lang/fa}. \n
                4- compile.\n

                Example: \n
                    1- extract -d .\n
                    2- init -l fa\n
                    3- go to ./lang/Fa/.po and add your translations.\n
                    4- compile\n

            If you have already extracted messages and you have an existing `.po` and `.mo` file
            follow this steps:\n
                1- extract -d/--dir {watch_dir} \n
                2- update -d/--dir {lang_dir} defaults is ./lang \n
                3- add your custome to your lang `.po` file for example FA dir {./lang/fa}. \n
                4- compile.

                Example: \n
                    1- extract -d .\n
                    2- update -d lang\n
                    3- go to ./lang/Fa/.po and add your translations.\n
                    4- compile\n
        """,  # noqa
        )
        def cmd():
            pass

        @cmd.command(
            "extract",
            help="""extract all messages that annotated using gettext/_
                in the specified directory.

                for first time will create messages.pot file into the root
                directory.""",
        )
        @option("-d", "--dir", "dir", help="watch dir")
        def extract(dir):
            try:
                self.extract(dir)
            except Exception as err:
                echo(err)

        @cmd.command(
            "init",
            help="""Initialized lacale directory for first time.
                if there is already exists the directory, notice that your
                all comiled and initialized messages will remove, in this
                condition has better to use `update` command""",
        )
        @option(
            "-l",
            "--lang",
            "lang",
            help="locale directory name and path, default is fa",
            default="fa",
        )
        def init(lang: Optional[str] = None):
            try:
                self.init(lang)
            except Exception as err:
                echo(err)

        @cmd.command(
            "compile",
            help="""compile all messages from translation directory in .PO to .MO file and is
                a binnary text file.""",
        )
        def compile():
            try:
                self.compile()
            except Exception as err:
                echo(err)

        @cmd.command(
            "update",
            help="""update the extracted messages after init command/initialized directory
                , Default is `./lang`""",
        )
        @option("-d", "--dir", "dir", help="locale directory name and path")
        def update(dir: Optional[str] = None):
            try:
                self.update(dir)
            except Exception as err:
                echo(err)

        cmd()


def initialize_babel_of_request(request: Request, babel_configs: RootConfigs, real_lang_code: str, jinja2_templates: Optional[Jinja2Templates] = None) -> Babel:
    # Create a new Babel instance per request
    babel = get_babel_in_request(request)
    if babel is None:
        request.state.babel = babel = Babel(configs=babel_configs)
        request.state.babel.locale = real_lang_code
        if jinja2_templates:
            request.state.babel.install_jinja(jinja2_templates)

    _context_var.set(
        request.state.babel.gettext
    )  # Set the _ function in the context variable
    _context_var_pgettext.set(
        request.state.babel.pgettext
    )
    return babel


LANGUAGES_PATTERN = re.compile(r"([a-z]{2})-?([A-Z]{2})?(;q=\d.\d{1,3})?")


def get_language_to_use(babel_configs: RootConfigs, lang_code: str | None) -> str:
    """Applies an available language.

    To apply an available language it will be searched in the language folder for an available one
    and will also priotize the one with the highest quality value. The Fallback language will be the
    taken from the BABEL_DEFAULT_LOCALE var.

        Args:
            babel (Babel): Request scoped Babel instance
            lang_code (str): The Value of the Accept-Language Header.

        Returns:
            str: The language that should be used.
    """
    if not lang_code:
        return babel_configs.BABEL_DEFAULT_LOCALE

    matches = re.finditer(LANGUAGES_PATTERN, lang_code)
    languages = [
        (f"{m.group(1)}{f'_{m.group(2)}' if m.group(2) else ''}", m.group(3) or "")
        for m in matches
    ]
    languages = sorted(
        languages, key=lambda x: x[1], reverse=True
    )  # sort the priority, no priority comes last
    translation_directory = Path(babel_configs.BABEL_TRANSLATION_DIRECTORY)
    translation_files = [i.name for i in translation_directory.iterdir()]
    explicit_priority = None

    for lang, quality in languages:
        if lang in translation_files:
            if (
                not quality
            ):  # languages without quality value having the highest priority 1
                return lang

            elif (
                not explicit_priority
            ):  # set language with explicit priority <= priority 1
                explicit_priority = lang

    # Return language with explicit priority or default value
    return (
        explicit_priority
        or (
            lang_code if any(map(lambda x: x.startswith(lang_code), translation_files)) else babel_configs.BABEL_DEFAULT_LOCALE
        )
    )


def get_babel_in_request(request: Request) -> Babel | None:
    return getattr(request.state, "babel", Babel.instance)


def require_babel_in_request(request: Request) -> Babel:
    babel = get_babel_in_request(request)
    if babel is None:
        raise BabelProxyError(
            "Babel instance is not available in the current request context."
        )
    return babel
