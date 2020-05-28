import os
from conans import ConanFile, tools, CMake
from conans.errors import ConanInvalidConfiguration
from conans.tools import Version


class LibuvConan(ConanFile):
    name = "libuv"
    version = "1.38.0"
    description = "Cross-platform asynchronous I/O "
    url = "https://github.com/bincrafters/conan-libuv"
    homepage = "https://github.com/libuv/libuv"
    topics = ("conan", "libuv", "io", "async", "event")
    license = "MIT"
    exports = ["LICENSE.md"]
    exports_sources = ["CMakeLists.txt"]
    settings = "os", "arch", "compiler", "build_type"
    generators = "cmake"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    @property
    def _source_subfolder(self):
        return "source_subfolder"

    @property
    def _is_mingw(self):
        return self.settings.os == "Windows" and self.settings.compiler != "Visual Studio"

    def configure(self):
        del self.settings.compiler.libcxx
        del self.settings.compiler.cppstd

    def source(self):
        tools.rmdir(self._source_subfolder)
        git = tools.Git(folder=self._source_subfolder)
        git.clone("https://github.com/Arenoros/libuv.git", 'v1.x')

    def _configure_cmake(self):
        cmake = CMake(self)
        cmake.definitions['CMAKE_INSTALL_PREFIX']='out'
        cmake.configure()
        return cmake

    def build(self):
        # TODO: GYP is not supported by MSVC 16
        cmake = self._configure_cmake()
        cmake.build()
        cmake.install()

    def package(self):
        self.copy(pattern="*", dst="include", src='out/include')
        if self.settings.os in ["Windows", "WindowsCE"]:
            self.copy(pattern="LICENSE*", dst="licenses", src='out')
            if self.options.shared:
                self.copy(pattern="uv.dll", dst="bin", src=f'out/lib/{self.settings.build_type}', keep_path=False)
                self.copy(pattern="uv.lib", dst="lib", src=f'out/lib/{self.settings.build_type}')
            else:
                self.copy(pattern="uv_a.lib", dst="lib/uv.lib", src=f'out/lib/{self.settings.build_type}')
        else:
            self.copy(pattern="*", dst="share", src='out/share')
            if self.options.shared:
                self.copy(pattern="libuv.so*", dst="lib", src='out/lib', symlinks=True, keep_path=False)
            else:
                self.copy(pattern="libuv_a.a", dst="lib", src='out/lib')

    def package_info(self):
        if self.settings.os in ["Windows", "WindowsCE"]:
            self.cpp_info.libs = ["uv.dll" if self.options.shared else "uv_a.lib"]
            self.cpp_info.libs.extend(["Psapi", "Ws2_32", "Iphlpapi", "Userenv"])
        else:
            self.cpp_info.libs = tools.collect_libs(self)
            if not self.settings.os in ["Android", "Neutrino"]:
                self.cpp_info.libs.append("pthread")
            if not self.settings.os in ["SunOS", 'AIX']:
                self.cpp_info.libs.append("dl")
            if self.settings.os == "SunOS":
                self.cpp_info.libs.extend(["kstat", "nsl", "sendfile", "socket"])
            if self.settings.os == "AIX":
                self.cpp_info.libs.extend(["perfstat"])
            