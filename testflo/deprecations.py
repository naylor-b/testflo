import sys
import os
import site

from io import StringIO

class DeprecationsReport(object):
    """Generates a report of all Deprecation warnings raised during testing."""

    def __init__(self, options, stream=sys.stdout):
        self.stream = stream
        self.options = options
        self.startdir = os.getcwd()

    def get_iter(self, input_iter):

        deprecations = {}

        for test in input_iter:
            for msg, locs in test.deprecations.items():
                deprecations[msg] = deprecations.get(msg, set()) | locs
            yield test

        report = self.generate_report(deprecations)

        if self.options.show_deprecations:
            self.stream.write(report)

        if self.options.deprecations_report:
            with open(self.options.deprecations_report, 'w') as stream:
                stream.write(report)

    def generate_report(self, deprecations):
        report = StringIO()

        title = " Deprecations Report "
        eqs = "=" * 30

        write = report.write

        write("\n{}{}{}\n".format(eqs, title, eqs))

        count = len(deprecations)

        write("\n\n{} unique deprecation warnings were captured{}\n\n".format(count, ':' if count else '.'))

        if count == 0 and self.options.disallow_deprecations:
            write("\nDeprecation warnings have been raised as Exceptions\n"
                  "due to the use of the --disallow_deprecations option,\n"
                  "so no deprecation warnings have been captured.")

        startdir = self.startdir
        try:
            sitedirs = site.getsitepackages()
        except:
            # python older than 3.2
            sitedirs = []

        def trim_path(path):
            # trim the start directory or the site-packages directory from the path
            if path.startswith(startdir):
                path = path[len(startdir):]
            else:
                for d in sitedirs:
                    if path.startswith(d):
                        path = path[len(d):]
            return path

        for msg in sorted(deprecations):
            write("--\n{}\n\n".format(msg))
            for filename, lineno, test_spec in deprecations[msg]:
                write("    {}, line {}\n".format(trim_path(filename), lineno))
                if test_spec:
                    write("    [{}]\n\n".format(trim_path(test_spec)))

        if count > 0:
            write("\n\nFor a stack trace of reported deprecations, run the "
                  "identified test with the --disallow_deprecations option.")

        write("\n" + "=" * (len(title) + 2 * len(eqs)) + "\n")

        return report.getvalue()
