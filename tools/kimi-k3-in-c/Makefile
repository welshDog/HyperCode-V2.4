# Minimal Makefile for Kimi K3 in C (CPU-only, OpenMP)

CC = gcc
CFLAGS = -O3 -std=c99 -fopenmp -Wall -Wextra -march=native
LDFLAGS = -fopenmp -lm

SRCS = k3.c k3_tensors.c k3_tokenizer.c main.c
OBJS = $(SRCS:.c=.o)
BIN = k3

.PHONY: all clean test

all: $(BIN)

$(BIN): $(OBJS)
	$(CC) $(LDFLAGS) -o $@ $^

%.o: %.c
	$(CC) $(CFLAGS) -c -o $@ $<

clean:
	rm -f $(OBJS) $(BIN)

# Tiny self-test against a reference model (same tensor graph as K3).
# This does NOT require the full 1.56 TB checkpoint.
test: $(BIN)
	@echo "Running self-tests..."
	@./$(BIN) --self-test
	@echo "All tests passed."
