import io
import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from selected_git import capture_version

class Reader:
    def __init__(self, target):
        target()
    def join(self, timeout):
        pass
    def is_alive(self):
        return False

class Process:
    def __init__(self, out=b'git version 2.54.0.windows.1\n', err=b'', code=0):
        self.stdout=io.BytesIO(out)
        self.stderr=io.BytesIO(err)
        self.code=code
        self.kills=0
        self.waits=0
    def poll(self):
        return self.code
    def kill(self):
        self.kills+=1
        self.code=-1
    def wait(self, timeout):
        self.waits+=1
        return self.code

class Resources:
    def __init__(self, proc=None):
        self.proc=proc or Process()
        self.calls=[]
        self.now=0.0
    def spawn(self, argv, **kwargs):
        self.calls.append((argv, kwargs))
        return self.proc
    def start_reader(self, target):
        return Reader(target)
    def clock(self):
        return self.now
    def tick(self, seconds):
        self.now+=seconds

class CaptureTests(unittest.TestCase):
    def test_observed_vendor_version_closes_and_reaps_selected_child_once(self):
        resources=Resources()
        result=capture_version(r'C:\Trusted Tools\git.exe', resources=resources, environment={})
        self.assertEqual(result, ('2.54.0.windows.1', None))
        self.assertEqual(resources.calls[0][0], [r'C:\Trusted Tools\git.exe','--version'])
        self.assertFalse(resources.calls[0][1]['shell'])
        self.assertEqual(resources.proc.waits,1)
        self.assertTrue(resources.proc.stdout.closed)
        self.assertTrue(resources.proc.stderr.closed)
        self.assertEqual(resources.proc.kills,0)

class CliTests(unittest.TestCase):
    def test_explicit_selected_version_is_observed_with_all_admission_flags_false(self):
        import contextlib
        import json
        import windows_onboarding
        resources=Resources()
        output=io.StringIO()
        with contextlib.redirect_stdout(output):
            code=windows_onboarding.main(['--git-executable',r'C:\Trusted Tools\git.exe'],
                                         resources=resources, platform='win32')
        result=json.loads(output.getvalue())
        self.assertEqual(code,0)
        self.assertEqual(result['git']['version'],'2.54.0.windows.1')
        self.assertEqual(result['git']['compatibility'],'unverified')
        self.assertEqual(result['git']['execution'],'observed')
        self.assertEqual(result['git']['discovery'],'not-probed')
        for flag in ('installation_admitted','filesystem_verified','source_verified'):
            self.assertFalse(result[flag])

class FailureTests(unittest.TestCase):
    def observe(self, proc, resources=None):
        return capture_version(r'C:\Tools\git.exe',resources=resources or Resources(proc),environment={})
    def test_supported_and_untested_ascii_versions(self):
        for token in ('0.1','999.123.4-vendor_2+build','2.54.0.windows.1'):
            for ending in (b'',b'\n',b'\r\n'):
                with self.subTest(token=token,ending=ending):
                    self.assertEqual(self.observe(Process(b'git version '+token.encode()+ending)),(token,None))
    def test_private_malformed_control_nonascii_multiline_and_stderr_are_not_returned(self):
        for out,err in ((b'',b''),(b'private-secret',b''),(b'git version 2.3\nextra',b''),
                        (b'git version 2.3\x00',b''),(b'git version 2.3\xff',b''),
                        (b'git version 2.3\r',b''),(b'git version 2.3\n',b'private-error')):
            with self.subTest(out=out):
                self.assertEqual(self.observe(Process(out,err)),(None,'invalid-output'))
    def test_nonzero_and_launch_failure_have_fixed_reasons(self):
        self.assertEqual(self.observe(Process(code=7)),(None,'nonzero-exit'))
        resources=Resources()
        def unavailable(*args,**kwargs):
            resources.calls.append(args)
            raise OSError('private-launch-error')
        resources.spawn=unavailable
        self.assertEqual(self.observe(None,resources),(None,'launch-failed'))
        self.assertEqual(len(resources.calls),1)
    def test_overflow_stops_reading_then_kills_reaps_and_closes(self):
        class CountingPipe(io.BytesIO):
            reads=0
            def read(self,n):
                self.reads+=1
                return super().read(n)
        proc=Process(code=None)
        proc.stdout=CountingPipe(b'x'*100000)
        resources=Resources(proc)
        self.assertEqual(self.observe(proc,resources),(None,'output-limit'))
        self.assertEqual(proc.stdout.reads,4097)
        self.assertEqual((proc.kills,proc.waits),(1,1))
        self.assertTrue(proc.stdout.closed and proc.stderr.closed)
    def test_combined_output_cap_is_shared_between_pipes(self):
        self.assertEqual(self.observe(Process(b'x'*2048,b'y'*2049)),(None,'output-limit'))
    def test_timeout_consumes_execution_deadline_and_cleans_up_once(self):
        proc=Process(code=None)
        resources=Resources(proc)
        self.assertEqual(self.observe(proc,resources),(None,'timeout'))
        self.assertGreaterEqual(resources.now,5)
        self.assertLess(resources.now,5.02)
        self.assertEqual((proc.kills,proc.waits),(1,1))
        self.assertTrue(proc.stdout.closed and proc.stderr.closed)
    def test_cleanup_failure_is_reported_without_retry_and_other_pipe_closes(self):
        class BrokenClose(io.BytesIO):
            attempts=0
            def close(self):
                self.attempts+=1
                raise OSError('private-close-error')
        proc=Process()
        proc.stdout=BrokenClose(b'git version 2.3\n')
        self.assertEqual(self.observe(proc),(None,'cleanup-failed'))
        self.assertEqual(proc.stdout.attempts,1)
        self.assertEqual(proc.waits,1)
        self.assertTrue(proc.stderr.closed)
    def test_environment_suppresses_helpers_config_transport_without_host_values(self):
        resources=Resources()
        capture_version(r'C:\Tools\git.exe',resources=resources,environment={
            'PATH':'private-path','GIT_EXEC_PATH':'private-helper','GIT_CONFIG_COUNT':'99',
            'SSH_ASKPASS':'private-askpass','SystemRoot':r'C:\Windows','TEMP':r'C:\Temp'})
        opts=resources.calls[0][1]
        self.assertEqual(opts['executable'],r'C:\Tools\git.exe')
        self.assertEqual(opts['stdin'],-3)
        self.assertTrue(opts['close_fds'])
        env=opts['env']
        self.assertNotIn('PATH',env)
        self.assertNotIn('GIT_EXEC_PATH',env)
        self.assertEqual(env['GIT_CONFIG_COUNT'],'4')
        self.assertEqual(env['GIT_ALLOW_PROTOCOL'],'')
        self.assertEqual(env['GIT_CONFIG_GLOBAL'],'NUL')
        self.assertEqual(env['SSH_ASKPASS'],'')
        self.assertEqual(env['SystemRoot'],r'C:\Windows')

class RefusalTests(unittest.TestCase):
    def cli(self,args,resources,platform='win32'):
        import contextlib,json,windows_onboarding
        output=io.StringIO()
        with contextlib.redirect_stdout(output):
            code=windows_onboarding.main(args,resources=resources,platform=platform)
        return code,json.loads(output.getvalue())
    def test_invalid_paths_and_arguments_never_launch(self):
        paths=('',r'git.exe',r'C:git.exe',r'\git.exe',r'\\server\share\git.exe',
               r'\\?\C:\git.exe',r'\\.\C:\git.exe',r'C:\a\..\git.exe',
               r'C:\a\.\git.exe',r'C:\a\git.exe:stream',r'C:\a*\git.exe',
               'C:\\a\x00\\git.exe','C:\\a\n\\git.exe',r'C:\a.\git.exe',
               r'C:\a \git.exe',r'C:\git.cmd',r'C:\git.ps1',r'C:\NUL.exe')
        args=[['--git-executable',path] for path in paths]
        args += [['--git-executable'],['--unknown'],['--git-executable',r'C:\git.exe','--git-executable',r'C:\git.exe']]
        from contextlib import ExitStack
        from unittest.mock import patch
        with ExitStack() as stack:
            controls=[stack.enter_context(patch(name,side_effect=AssertionError('discovery or launch forbidden')))
                      for name in ('shutil.which','os.stat','os.lstat','os.access','os.scandir',
                                   'os.listdir','builtins.open','subprocess.Popen','subprocess.run',
                                   'selected_git.ProcessResources.spawn','selected_git.ProcessResources.start_reader')]
            controls.append(stack.enter_context(patch.object(Resources,'spawn',side_effect=AssertionError('fake launch forbidden'))))
            for control in controls:
                with self.assertRaises(AssertionError):
                    control('positive-control')
            for arg in args:
                resources=Resources()
                code,result=self.cli(arg,resources)
                self.assertEqual(code,2)
                self.assertEqual(result['status'],'blocked')
                self.assertEqual(resources.calls,[])
                self.assertFalse(result['installation_admitted'])
    def test_spaces_unicode_and_forward_slashes_are_lexical_not_confinement(self):
        from selected_git import valid_selection
        for path in (r'C:\Trusted Tools\git.exe','D:\\工具\\git.EXE','C:/Tools/git.exe'):
            self.assertTrue(valid_selection(path))
    def test_unsupported_runtime_refuses_without_launch(self):
        resources=Resources()
        code,result=self.cli(['--git-executable',r'C:\Tools\git.exe'],resources,'linux')
        self.assertEqual((code,result['error']),(2,'unsupported-platform'))
        self.assertEqual(resources.calls,[])
    def test_failure_report_preserves_runtime_and_false_flags_without_private_output(self):
        resources=Resources(Process(b'private-payload'))
        code,result=self.cli(['--git-executable',r'C:\Tools\git.exe'],resources)
        self.assertEqual((code,result['error']),(1,'invalid-output'))
        self.assertIn('runtime',result)
        self.assertEqual(result['git']['availability'],'unverified')
        self.assertEqual(result['git']['version'],'unverified')
        self.assertNotIn('private',str(result))
        for flag in ('installation_admitted','filesystem_verified','source_verified'):
            self.assertFalse(result[flag])
    def test_passive_report_unchanged_and_help_launches_nothing(self):
        import contextlib,json,windows_onboarding
        resources=Resources()
        code,result=self.cli([],resources)
        self.assertEqual((code,result),(0,windows_onboarding.report()))
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(windows_onboarding.main(['--help'],resources=resources),0)
        self.assertEqual(resources.calls,[])

class DeadlineAndControlTests(unittest.TestCase):
    def test_late_completed_child_does_not_bypass_execution_deadline(self):
        resources=Resources()
        def late_poll():
            resources.now=6.0
            return 0
        resources.proc.poll=late_poll
        result=capture_version(r'C:\Tools\git.exe',resources=resources,environment={})
        self.assertEqual(result,(None,'timeout'))
        self.assertEqual(resources.proc.waits,1)
    def test_unicode_control_character_refuses_lexically(self):
        from selected_git import valid_selection
        self.assertFalse(valid_selection('C:\\a\u0085\\git.exe'))

class CleanupResourceTests(unittest.TestCase):
    def test_reader_start_kill_wait_and_reader_join_failures_do_not_retry(self):
        for failure in ('start','kill','wait','join','alive'):
            resources=Resources(Process(code=None if failure=='kill' else 0))
            counts={'operation':0}
            def broken(*args,**kwargs):
                counts['operation']+=1
                raise OSError('private-resource-error')
            if failure=='start':
                resources.start_reader=broken
            elif failure=='kill':
                resources.proc.stdout=io.BytesIO(b'x'*4097)
                resources.proc.kill=broken
            elif failure=='wait':
                resources.proc.wait=broken
            else:
                def reader(target):
                    r=Reader(target)
                    if failure=='alive':
                        r.is_alive=lambda: True
                    else:
                        def fail_join(timeout):
                            counts['operation']+=1
                            raise RuntimeError('private-reader-error')
                        r.join=fail_join
                    return r
                resources.start_reader=reader
            with self.subTest(failure=failure):
                self.assertEqual(capture_version(r'C:\Tools\git.exe',resources=resources,environment={}),
                                 (None,'cleanup-failed'))
                self.assertTrue(resources.proc.stdout.closed and resources.proc.stderr.closed)
                self.assertEqual(len(resources.calls),1)
                if failure in ('start','kill','wait'):
                    self.assertEqual(counts['operation'],1)

class ObservationFailureTests(unittest.TestCase):
    def test_explicit_runtime_observation_failure_never_launches_or_echoes(self):
        import contextlib,json,windows_onboarding
        from unittest.mock import patch
        resources=Resources()
        output=io.StringIO()
        with patch.object(windows_onboarding,'report',side_effect=OSError('private-error')):
            with contextlib.redirect_stdout(output):
                code=windows_onboarding.main(['--git-executable',r'C:\Tools\git.exe'],resources=resources,platform='win32')
        result=json.loads(output.getvalue())
        self.assertEqual((code,result['error']),(1,'observation-unavailable'))
        self.assertEqual(resources.calls,[])
        self.assertNotIn('private',output.getvalue())
        self.assertEqual(result['git']['availability'],'unverified')

class FailureReportMatrixTests(unittest.TestCase):
    def test_each_requested_failure_has_fixed_json_exit_and_unverified_fields(self):
        import contextlib,json,windows_onboarding
        for reason in ('launch-failed','timeout','output-limit','invalid-output','nonzero-exit','cleanup-failed'):
            resources=Resources()
            if reason=='launch-failed':
                def fail(*args,**kwargs):
                    raise OSError('private-error')
                resources.spawn=fail
            elif reason=='timeout':
                resources.proc.code=None
            elif reason=='output-limit':
                resources.proc.stdout=io.BytesIO(b'x'*4097)
            elif reason=='invalid-output':
                resources.proc.stdout=io.BytesIO(b'private-invalid')
            elif reason=='nonzero-exit':
                resources.proc.code=2
            else:
                def fail_wait(timeout):
                    raise OSError('private-error')
                resources.proc.wait=fail_wait
            output=io.StringIO()
            with self.subTest(reason=reason),contextlib.redirect_stdout(output):
                code=windows_onboarding.main(['--git-executable',r'C:\Tools\git.exe'],resources=resources,platform='win32')
                result=json.loads(output.getvalue())
                self.assertEqual((code,result['error'],result['status']),(1,reason,'blocked'))
                for key in ('availability','version','compatibility'):
                    self.assertEqual(result['git'][key],'unverified')
                self.assertEqual(result['git']['discovery'],'not-probed')
                for flag in ('installation_admitted','filesystem_verified','source_verified'):
                    self.assertFalse(result[flag])
                self.assertNotIn('private',output.getvalue())
