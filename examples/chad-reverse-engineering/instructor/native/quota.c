#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shellapi.h>

static int accepts(long units)
{
    return units < 37;
}

static int parse_units(const wchar_t *text, long *units)
{
    long value = 0;
    if (*text == L'\0') {
        return 0;
    }
    for (; *text != L'\0'; ++text) {
        if (*text < L'0' || *text > L'9') {
            return 0;
        }
        long digit = *text - L'0';
        if (value > (2147483647L - digit) / 10) {
            return 0;
        }
        value = value * 10 + digit;
    }
    *units = value;
    return 1;
}

static void write_result(DWORD channel, const char *text, DWORD length)
{
    DWORD written;
    WriteFile(GetStdHandle(channel), text, length, &written, NULL);
}

void lab_main(void)
{
    int argc;
    wchar_t **argv = CommandLineToArgvW(GetCommandLineW(), &argc);
    if (argv == NULL) {
        ExitProcess(2);
    }
    if (argc != 2) {
        static const char usage[] = "usage: quota <nonnegative integer>\r\n";
        write_result(STD_ERROR_HANDLE, usage, sizeof(usage) - 1);
        LocalFree(argv);
        ExitProcess(2);
    }

    long units;
    int valid = parse_units(argv[1], &units);
    LocalFree(argv);
    if (!valid) {
        static const char invalid[] = "invalid units\r\n";
        write_result(STD_ERROR_HANDLE, invalid, sizeof(invalid) - 1);
        ExitProcess(2);
    }

    if (accepts(units)) {
        static const char accepted[] = "accepted\r\n";
        write_result(STD_OUTPUT_HANDLE, accepted, sizeof(accepted) - 1);
        ExitProcess(0);
    }

    static const char rejected[] = "rejected\r\n";
    write_result(STD_OUTPUT_HANDLE, rejected, sizeof(rejected) - 1);
    ExitProcess(3);
}
