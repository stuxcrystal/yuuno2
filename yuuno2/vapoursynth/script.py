import types
from typing import NoReturn, Mapping, Union, Any, Sequence

from vapoursynth import Environment, vpy_current_environment
from vapoursynth import get_outputs, get_core, Core

from yuuno2.clip import Clip
from yuuno2.providers.single import SingleScriptProvider
from yuuno2.script import Script, NOT_GIVEN
from yuuno2.typings import ConfigTypes
from yuuno2.vapoursynth.clip import VapourSynthClip


class VapourSynthScript(Script):

    def __init__(self, environment: Environment):
        self.module = types.ModuleType("__vapoursynth__")
        self.config = {}
        self.environment = environment

    def activate(self) -> NoReturn:
        self.environment.__enter__()

    def deactivate(self) -> NoReturn:
        self.environment.__exit__(None, None, None)

    async def set_config(self, key: str, value: ConfigTypes) -> NoReturn:
        await self.ensure_acquired()
        self.config[key] = value
        if key.startswith('vs.core.'):
            key = key[len('vs.core.'):]
            with self.inside():
                setattr(get_core(), key, value)

    async def get_config(self, key: str, default: Union[object, ConfigTypes] = NOT_GIVEN) -> ConfigTypes:
        await self.ensure_acquired()
        value = self.config.get(key, default)
        if value is NOT_GIVEN:
            raise KeyError(key)
        return value

    async def list_config(self) -> Sequence[str]:
        await self.ensure_acquired()
        return list(self.config.keys())

    async def run(self, code: Union[bytes, str]) -> Any:
        await self.ensure_acquired()
        with self.inside():
            exec(code)

    async def retrieve_clips(self) -> Mapping[str, Clip]:
        await self.ensure_acquired()
        with self.inside():
            outputs = get_outputs().items()
        return {k: VapourSynthClip(self, d) for k, d in outputs}

    async def _acquire(self) -> NoReturn:
        with self.environment:
            core: Core = get_core()
            self.config.update({
                'vs.core.add_cache': core.add_cache,
                'vs.core.num_threads': core.num_threads,
                'vs.core.max_cache_size': core.max_cache_size,
            })

    async def _release(self) -> NoReturn:
        pass

    async def ensure_acquired(self) -> NoReturn:
        if not self.environment.alive:
            await self.release()
            raise EnvironmentError("Environment has been destroyed.")
        return (await super().ensure_acquired())


def VapourSynthScriptManager():
    return SingleScriptProvider(
        VapourSynthScript(vpy_current_environment()),
    )