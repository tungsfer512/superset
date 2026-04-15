/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */
import { Menu } from '@superset-ui/core/components';
import type { MenuItem, MenuItemType } from '@superset-ui/core/components/Menu';
import { useThemeContext } from 'src/theme/ThemeProvider';
import { useThemeMenuItems } from 'src/hooks/useThemeMenuItems';

export interface ThemePickerProps {
  className?: string;
  menuMode?: 'horizontal' | 'vertical';
}

function isMenuItemType(item: MenuItem): item is MenuItemType {
  return Boolean(item && typeof item === 'object' && 'key' in item);
}

export default function ThemePicker({
  className,
  menuMode = 'horizontal',
}: ThemePickerProps) {
  const {
    setThemeMode,
    themeMode,
    clearLocalOverrides,
    hasDevOverride,
    canSetMode,
    canDetectOSPreference,
  } = useThemeContext();
  const canShowThemePicker = canSetMode();

  const themeMenuItem = useThemeMenuItems({
    setThemeMode,
    themeMode,
    hasLocalOverride: hasDevOverride(),
    onClearLocalSettings: clearLocalOverrides,
    allowOSPreference: canDetectOSPreference(),
  });

  if (!canShowThemePicker) {
    return null;
  }

  if (!isMenuItemType(themeMenuItem)) {
    return null;
  }

  const themeMenuItemWithClass: MenuItem = {
    ...themeMenuItem,
    className: [themeMenuItem.className || '', 'theme-submenu-with-caret']
      .filter(Boolean)
      .join(' '),
  };

  return (
    <Menu
      className={className}
      selectable={false}
      mode={menuMode}
      items={[themeMenuItemWithClass]}
    />
  );
}
