# Build libbestprime from the generated OpenMP core.
#   make -C native
#   make -C native prefix=/usr/local install
ROOT    := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/..)
DATA    := $(ROOT)/is_prime_data
INCLUDE := $(ROOT)/include
PREFIX  ?= /usr/local

UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Darwin)
  SO    := libbestprime.dylib
  SOFLAGS := -dynamiclib -install_name $(PREFIX)/lib/$(SO)
  OPENMP ?= -Xpreprocessor -fopenmp -lomp
else
  SO    := libbestprime.so
  SOFLAGS := -shared -Wl,-soname,$(SO)
  OPENMP ?= -fopenmp
endif

CC      ?= gcc
CFLAGS  ?= -O3 -fPIC -funroll-loops -fomit-frame-pointer
ARCH    ?=
LDFLAGS ?= -lm

.PHONY: all generate install uninstall clean

all: $(DATA)/$(SO)

$(DATA)/wheel_core.c:
	python3 $(ROOT)/scripts/generate_wheel_core_c.py

$(DATA)/$(SO): $(DATA)/wheel_core.c
	$(CC) $(CFLAGS) $(ARCH) $(SOFLAGS) $(OPENMP) -o $@ $< $(LDFLAGS) $(OPENMP)
	# Also drop the historical ctypes name next to the library.
	cp -f $@ $(DATA)/wheel_core$(suffix $(SO))

generate: $(DATA)/wheel_core.c

install: all
	install -d $(PREFIX)/include $(PREFIX)/lib $(PREFIX)/lib/pkgconfig
	install -m 644 $(INCLUDE)/best_prime.h $(PREFIX)/include/best_prime.h
	install -m 755 $(DATA)/$(SO) $(PREFIX)/lib/$(SO)
	sed -e 's|@PREFIX@|$(PREFIX)|g' -e 's|@VERSION@|1.11.2|g' \
	    $(ROOT)/pkgconfig/best_prime.pc.in > $(PREFIX)/lib/pkgconfig/best_prime.pc

uninstall:
	rm -f $(PREFIX)/include/best_prime.h \
	      $(PREFIX)/lib/$(SO) \
	      $(PREFIX)/lib/pkgconfig/best_prime.pc

clean:
	rm -f $(DATA)/libbestprime.so $(DATA)/libbestprime.dylib
