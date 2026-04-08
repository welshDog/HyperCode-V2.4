package main

import "testing"

func BenchmarkCompileBF(b *testing.B) {
	source := "++++[>++++<-]>.[-],<.[>+<-]"
	for i := 0; i < b.N; i++ {
		_ = compileBF(source)
	}
}

