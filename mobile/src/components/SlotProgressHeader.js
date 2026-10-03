import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { NeoColors } from '../theme/neomorphism';
import NeoCard from './NeoCard';

export default function SlotProgressHeader({ slotProgress, activeSlotId, onTriggerSlot }) {
  const slots = [
    {
      id: 1,
      name: 'Morning',
      time: '4am - 11am',
      icon: '🌅',
      theme: 'Fundamentals',
    },
    {
      id: 2,
      name: 'Afternoon',
      time: '11am - 5pm',
      icon: '☀️',
      theme: 'Architecture',
    },
    {
      id: 3,
      name: 'Evening',
      time: '5pm - 12am',
      icon: '🌙',
      theme: 'Scenarios',
    },
  ];

  const getSlotStatus = (slotId) => {
    if (!slotProgress) return { label: 'Upcoming', color: '#64748b', bg: '#f1f5f9' };
    const p = slotProgress[String(slotId)] || slotProgress[slotId];
    if (!p) return { label: 'Upcoming', color: '#64748b', bg: '#f1f5f9' };

    if (p.executed || p.status === 'completed') {
      return {
        label: `✓ Done (${p.question_count || 0})`,
        color: '#059669',
        bg: 'rgba(16, 185, 129, 0.12)',
      };
    }
    if (p.status === 'skipped') {
      return {
        label: '⊘ Skipped',
        color: '#94a3b8',
        bg: 'rgba(148, 163, 184, 0.15)',
      };
    }
    if (activeSlotId === slotId) {
      return {
        label: '● Active Now',
        color: '#2563eb',
        bg: 'rgba(37, 99, 235, 0.12)',
      };
    }
    return { label: 'Pending', color: '#d97706', bg: 'rgba(217, 119, 6, 0.1)' };
  };

  return (
    <NeoCard style={styles.container}>
      <View style={styles.titleRow}>
        <Text style={styles.title}>📅 Daily 3-Slot Prep Tracker</Text>
        <Text style={styles.subtitle}>Only 3 batches per day (No spam)</Text>
      </View>

      <View style={styles.slotsRow}>
        {slots.map((s) => {
          const status = getSlotStatus(s.id);
          const isActive = activeSlotId === s.id;
          return (
            <View
              key={s.id}
              style={[
                styles.slotItem,
                isActive && styles.slotItemActive,
              ]}
            >
              <Text style={styles.slotIcon}>{s.icon}</Text>
              <Text style={styles.slotName}>{s.name}</Text>
              <Text style={styles.slotTime}>{s.time}</Text>

              <View style={[styles.statusBadge, { backgroundColor: status.bg }]}>
                <Text style={[styles.statusText, { color: status.color }]}>
                  {status.label}
                </Text>
              </View>
            </View>
          );
        })}
      </View>
    </NeoCard>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: 12,
    marginBottom: 14,
  },
  titleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  title: {
    fontSize: 12,
    fontWeight: '800',
    color: NeoColors.textPrimary,
  },
  subtitle: {
    fontSize: 10,
    color: NeoColors.textMuted,
  },
  slotsRow: {
    flexDirection: 'row',
    gap: 8,
  },
  slotItem: {
    flex: 1,
    backgroundColor: '#f1f5fa',
    borderRadius: 10,
    padding: 8,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#dce5f2',
  },
  slotItemActive: {
    borderColor: '#4f46e5',
    backgroundColor: '#edf2fc',
  },
  slotIcon: {
    fontSize: 18,
    marginBottom: 2,
  },
  slotName: {
    fontSize: 11,
    fontWeight: '700',
    color: NeoColors.textPrimary,
  },
  slotTime: {
    fontSize: 9,
    color: NeoColors.textMuted,
    marginBottom: 6,
  },
  statusBadge: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 6,
  },
  statusText: {
    fontSize: 9,
    fontWeight: '700',
  },
});
