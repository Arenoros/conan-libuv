import os
from conans import ConanFile, tools, CMake
from conans.errors import ConanInvalidConfiguration
from conans.tools import Version


class LibuvConan(ConanFile):
    name = "libuv"
    version = "1.31.0"
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

    @property
    def _is_msvc16(self):
        return self.settings.os == "Windows" and self.settings.compiler == "Visual Studio" and \
            Version(self.settings.compiler.version) == "16"

    def configure(self):
        del self.settings.compiler.libcxx
        del self.settings.compiler.cppstd
        if self.settings.compiler == "Visual Studio" \
            and int(str(self.settings.compiler.version)) < 14:
            raise ConanInvalidConfiguration("Visual Studio >= 14 (2015) is required")

    def source(self):
        sha256 = "ab041ea5d1965a33d4e03ea87718b8922ba4e54abb46c71cf9e040edef2556c0"
        tools.get("{0}/archive/v{1}.tar.gz".format(self.homepage, self.version), sha256=sha256)
        extracted_folder = self.name + "-" + self.version
        os.rename(extracted_folder, self._source_subfolder)

    def build_requirements(self):
        self.build_requires("gyp_installer/20190423@bincrafters/stable")
        if not tools.which("ninja"):
            self.build_requires("ninja/1.9.0")

    def _configure_cmake(self):
        cmake = CMake(self)
        cmake.configure()
        return cmake

    def build(self):
        # TODO: GYP is not supported by MSVC 16
        if self._is_mingw or self._is_msvc16:
            cmake = self._configure_cmake()
            cmake.build()
        else:
            with tools.chdir(self._source_subfolder):
                env_vars = dict()
                if self.settings.compiler == "Visual Studio":
                    env_vars["GYP_MSVS_VERSION"] = {"14": "2015",
                                                    "15": "2017"}.get(str(self.settings.compiler.version))
                with tools.environment_append(env_vars):
                    target_arch = {"x86": "ia32", "x86_64": "x64"}.get(str(self.settings.arch))
                    uv_library = "shared_library" if self.options.shared else "static_library"
                    self.run("python gyp_uv.py -f ninja -Dtarget_arch=%s -Duv_library=%s"
                            % (target_arch, uv_library))
                    self.run("ninja -C out/%s" % self.settings.build_type)

    def package(self):
        self.copy(pattern="LICENSE*", dst="licenses", src=self._source_subfolder)
        self.copy(pattern="*.h", dst="include", src=os.path.join(self._source_subfolder, "include"))
        bin_dir = os.path.join(self._source_subfolder, "out", str(self.settings.build_type))
        if self.settings.os == "Windows":
            if self.options.shared:
                self.copy(pattern="*.dll", dst="bin", src=bin_dir, keep_path=False)
                self.copy(pattern="*.dll", dst="bin", src="bin")
                self.copy(pattern="libuv.dll.a", dst="lib", src="lib")
                self.copy(pattern="uv.lib", dst="lib", src="lib")
            else:
                self.copy(pattern="libuv_a.a", dst="lib", src="lib")
                self.copy(pattern="uv_a.lib", dst="lib", src="lib")
            self.copy(pattern="*.lib", dst="lib", src=bin_dir, keep_path=False)
        elif str(self.settings.os) in ["Linux", "Android"]:
            if self.options.shared:
                self.copy(pattern="libuv.so.1", dst="lib", src=os.path.join(bin_dir, "lib"),
                        keep_path=False)
                lib_dir = os.path.join(self.package_folder, "lib")
                os.symlink("libuv.so.1", os.path.join(lib_dir, "libuv.so"))
            else:
                self.copy(pattern="*.a", dst="lib", src=bin_dir, keep_path=False)
        elif str(self.settings.os) in ["Macos", "iOS", "watchOS", "tvOS"]:
            if self.options.shared:
                self.copy(pattern="*.dylib", dst="lib", src=bin_dir, keep_path=False)
            else:
                self.copy(pattern="*.a", dst="lib", src=bin_dir, keep_path=False)

    def package_info(self):
        if self.settings.os == "Windows":
            if self._is_mingw:
                self.cpp_info.libs = ["libuv.dll.lib" if self.options.shared else "uv_a"]
            elif self._is_msvc16:
                self.cpp_info.libs = ["uv" if self.options.shared else "uv_a"]
            else:
                self.cpp_info.libs = ["libuv.dll.lib" if self.options.shared else "libuv"]
            self.cpp_info.libs.extend(["Psapi", "Ws2_32", "Iphlpapi", "Userenv"])
        else:
            self.cpp_info.libs = tools.collect_libs(self)
        if self.settings.os == "Linux":
            self.cpp_info.libs.append("pthread")
