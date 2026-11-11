/* A test of the SharedCLibrary in the ROM: an application that calls into each part of the library and
 * says what failed. "sh build.sh clibtest" builds it as build/<machine>/clibtest,ff8; run it from a
 * filing system it can write to. It ends with "ALL OK" or the number of failures. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <setjmp.h>
#include <stdarg.h>
#include <time.h>
#include <signal.h>
#include <errno.h>
#include <ctype.h>
#include <locale.h>

static int fails;

static void check(const char *what, int ok)
{
    printf("%s:%s  ", what, ok ? "ok" : "FAIL");
    if (!ok) fails++;
}

static int vformat(char *buf, const char *fmt, ...)
{
    va_list ap;
    int n;
    va_start(ap, fmt);
    n = vsprintf(buf, fmt, ap);
    va_end(ap);
    return n;
}

static int sum(int n, ...)
{
    va_list ap;
    int t = 0;
    double d = 0;
    va_start(ap, n);
    while (n--) { t += va_arg(ap, int); d += va_arg(ap, double); }
    va_end(ap);
    return t + (int)d;
}

static int compare(const void *a, const void *b) { return *(const int *)a - *(const int *)b; }

static int deep(int n)
{
    volatile char pad[1024];
    pad[0] = (char)n;
    return n ? deep(n - 1) + pad[0] - (char)n + 1 : 0;
}

static jmp_buf jb;
static int caught;
static void handler(int sig) { caught = sig; }
static void bye(void) { printf("atexit:ok\n%s\n", fails ? "FAILED" : "ALL OK"); }

static int near(double a, double b) { return fabs(a - b) < 1e-9; }

int main(int argc, char **argv)
{
    char buf[256], line[64];
    int i, a[50], key = 37, *found;
    volatile int v7 = 7, vm = -1000;
    char *blocks[100], *big, *end;
    FILE *f;
    double d;
    time_t now;
    div_t q;

    atexit(bye);
    check("argv", argc >= 1 && argv[0] != NULL);

    sprintf(buf, "%d %5.2f %s %x %c %ld %05u|%-4d|%e", -42, 3.14159, "str", 0xBEEF, 'q', 123456789L, 42u, 7, 1234.5);
    check("sprintf", strcmp(buf, "-42  3.14 str beef q 123456789 00042|7   |1.234500e+03") == 0);
    check("vsprintf", vformat(buf, "%s-%d-%g", "va", 99, 0.5) == 9 && strcmp(buf, "va-99-0.5") == 0);
    check("va_arg", sum(3, 1, 1.5, 2, 2.5, 3, 3.0) == 13);
    check("sscanf", sscanf("12 abc 2.5", "%d %s %lf", &i, line, &d) == 3 && i == 12 && !strcmp(line, "abc") && d == 2.5);

    for (i = 0; i < 100; i++) { blocks[i] = malloc(100 + i * 7); if (blocks[i]) memset(blocks[i], i, 100 + i * 7); }
    for (i = 0; i < 100 && blocks[i] && blocks[i][99 + i * 7] == i; i++) ;
    check("malloc", i == 100);
    blocks[0] = realloc(blocks[0], 5000);
    check("realloc", blocks[0] && blocks[0][99] == 0);
    for (i = 0; i < 100; i++) free(blocks[i]);
    big = calloc(300, 1024);
    check("calloc 300K", big && big[300 * 1024 - 1] == 0);
    free(big);

    for (i = 0; i < 50; i++) a[i] = (i * 37) % 50;
    qsort(a, 50, sizeof a[0], compare);
    for (i = 0; i < 50 && a[i] == i; i++) ;
    found = bsearch(&key, a, 50, sizeof a[0], compare);
    check("qsort", i == 50);
    check("bsearch", found == &a[37]);

    i = setjmp(jb);
    if (i == 0) longjmp(jb, 5);
    check("longjmp", i == 5);

    strcpy(buf, "one,two;three");
    check("strtok", !strcmp(strtok(buf, ",;"), "one") && !strcmp(strtok(NULL, ",;"), "two") && !strcmp(strtok(NULL, ",;"), "three"));
    check("strstr", strstr("haystack", "st") != NULL && strchr("abc", 'c') != NULL && strlen("12345") == 5);
    strcpy(buf, "abcdef");
    memmove(buf + 2, buf, 4);
    check("memmove", !memcmp(buf, "ababcd", 6));
    check("strtod", strtod("1.5e3x", &end) == 1500.0 && *end == 'x' && atoi("-17") == -17 && strtol("ff", NULL, 16) == 255);

    check("sqrt", near(sqrt(2.0) * sqrt(2.0), 2.0));
    check("sin cos", near(sin(1.0) * sin(1.0) + cos(1.0) * cos(1.0), 1.0));
    check("exp log", near(log(exp(3.0)), 3.0) && near(log10(1000.0), 3.0));
    check("pow", near(pow(2.0, 10.0), 1024.0) && near(pow(9.0, 0.5), 3.0));
    check("atan", near(4 * atan(1.0), 3.14159265358979) && near(atan2(1.0, 1.0) * 4, 3.14159265358979));
    check("floor", floor(-2.5) == -3.0 && ceil(2.1) == 3.0 && fmod(7.5, 2.0) == 1.5 && fabs(-2.0) == 2.0);
    check("fp to int", (int)(d = 1e6 / 3) == 333333 && (double)v7 / 2 == 3.5);
    check("divide", vm / v7 == -142 && vm % v7 == -6 && (unsigned)vm / 1000u == 4294966u);
    q = div(17, 5);
    check("div", q.quot == 3 && q.rem == 2 && abs(-3) == 3);

    f = fopen("clibtmp", "w");
    if (f) { fprintf(f, "line %d\nsecond\n", 1); fputc('x', f); }
    check("fopen w", f != NULL && fclose(f) == 0);
    f = fopen("clibtmp", "r");
    check("fgets", f && fgets(line, sizeof line, f) && !strcmp(line, "line 1\n"));
    check("fseek", f && fseek(f, -1L, SEEK_END) == 0 && ftell(f) == 14 && fgetc(f) == 'x' && fgetc(f) == EOF && feof(f));
    if (f) fclose(f);
    check("remove", remove("clibtmp") == 0 && fopen("clibtmp", "r") == NULL);

    now = time(NULL);
    i = strftime(buf, sizeof buf, "%Y", localtime(&now));
    check("time", now != (time_t)-1 && localtime(&now)->tm_year > 90 && i == 4);
    if (i != 4 || localtime(&now)->tm_year <= 90) printf("[%lu year %d %d \"%s\"] ", (unsigned long)now, localtime(&now)->tm_year, i, buf);
    check("clock", clock() != (clock_t)-1);
    check("getenv", getenv("Sys$Time") != NULL && getenv("No$Such$Var") == NULL);
    check("ctype", isalpha('a') && !isalpha('1') && isdigit('7') && toupper('x') == 'X' && isspace(' '));
    check("locale", setlocale(LC_ALL, "C") != NULL && localeconv()->decimal_point[0] == '.');
    srand(1);
    i = rand();
    srand(1);
    check("rand", rand() == i);
    errno = 0;
    d = sqrt(-1.0);
    check("errno", errno == EDOM);

    signal(SIGINT, handler);
    raise(SIGINT);
    check("signal", caught == SIGINT);
    check("stack 200K", deep(200) == 200);
    check("system", system("Set CLib$Test done") == 0 && !strcmp(getenv("CLib$Test"), "done"));
    return 0;
}
