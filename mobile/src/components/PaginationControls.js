import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { NeoColors } from '../theme/neomorphism';

export default function PaginationControls({
  page,
  totalPages,
  totalItems,
  onPrev,
  onNext,
}) {
  return (
    <View style={styles.container}>
      <TouchableOpacity
        onPress={onPrev}
        disabled={page <= 1}
        style={[styles.btn, page <= 1 && styles.btnDisabled]}
      >
        <Text style={[styles.btnText, page <= 1 && styles.btnTextDisabled]}>
          ◀ Prev
        </Text>
      </TouchableOpacity>

      <View style={styles.infoBox}>
        <Text style={styles.pageText}>
          Page <Text style={styles.bold}>{page}</Text> of {Math.max(1, totalPages)}
        </Text>
        {totalItems !== undefined ? (
          <Text style={styles.subText}>{totalItems} saved items</Text>
        ) : null}
      </View>

      <TouchableOpacity
        onPress={onNext}
        disabled={page >= totalPages}
        style={[styles.btn, page >= totalPages && styles.btnDisabled]}
      >
        <Text style={[styles.btnText, page >= totalPages && styles.btnTextDisabled]}>
          Next ▶
        </Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 14,
    paddingHorizontal: 10,
    marginTop: 6,
    marginBottom: 20,
    backgroundColor: '#ebf1f8',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#d5e0ee',
  },
  btn: {
    backgroundColor: '#ffffff',
    paddingVertical: 8,
    paddingHorizontal: 14,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#c5d2e3',
  },
  btnDisabled: {
    opacity: 0.4,
    backgroundColor: '#e2e8f0',
  },
  btnText: {
    fontSize: 12,
    fontWeight: '700',
    color: '#1e293b',
  },
  btnTextDisabled: {
    color: '#94a3b8',
  },
  infoBox: {
    alignItems: 'center',
  },
  pageText: {
    fontSize: 12,
    color: NeoColors.textSecondary,
  },
  bold: {
    fontWeight: '800',
    color: NeoColors.textPrimary,
  },
  subText: {
    fontSize: 10,
    color: NeoColors.textMuted,
    marginTop: 1,
  },
});
