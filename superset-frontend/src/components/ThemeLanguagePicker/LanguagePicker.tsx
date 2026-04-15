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
import { useCallback } from 'react';
import { Menu } from '@superset-ui/core/components';
import {
    Languages,
    useLanguageMenuItems,
} from 'src/features/home/LanguagePicker';
import type {
    MenuItem,
    MenuItemType,
} from '@superset-ui/core/components/Menu';

export interface LanguagePickerProps {
    className?: string;
    locale: string;
    languages: Languages;
    menuMode?: 'horizontal' | 'vertical';
}

function isSubmenuItem(item: MenuItem): item is MenuItemType & { children: MenuItem[] } {
    return Boolean(item && typeof item === 'object' && 'children' in item);
}

function isClickableMenuItem(item: MenuItem): item is MenuItemType {
    return Boolean(item && typeof item === 'object' && 'key' in item);
}

export default function LanguagePicker({
    className,
    locale,
    languages,
    menuMode = 'horizontal',
}: LanguagePickerProps) {
    const languageKeys = Object.keys(languages);

    if (!languageKeys.length) {
        return null;
    }

    const safeLocale = languages[locale] ? locale : languageKeys[0];
    const languageMenuItem = useLanguageMenuItems({
        locale: safeLocale,
        languages,
    });

    const handleLanguageChange = useCallback(
        async (langKey: string) => {
            const url = languages[langKey]?.url;
            if (url && url !== '#') {
                // Call locale endpoint in background to update server session
                // We use redirect: 'manual' to avoid navigating away from the page
                await fetch(url, {
                    method: 'GET',
                    credentials: 'include',
                    redirect: 'manual',
                });
                // If inside an iframe (embedded mode), notify the parent to re-embed
                // instead of reloading the iframe (which breaks the SDK MessagePort)
                if (window.parent !== window) {
                    window.parent.postMessage(
                        { type: 'superset-locale-changed', locale: langKey },
                        '*',
                    );
                } else {
                    window.location.reload();
                }
            }
        },
        [languages],
    );

    if (!isSubmenuItem(languageMenuItem)) {
        return null;
    }

    // Override children items to add onClick handlers instead of href
    const languageMenuItemWithClass = {
        ...languageMenuItem,
        className: [languageMenuItem.className || '', 'language-submenu-with-caret']
            .filter(Boolean)
            .join(' '),
        children: languageMenuItem.children
            ?.filter(isClickableMenuItem)
            .map(item => ({
                ...item,
                onClick: () => handleLanguageChange(String(item.key)),
            })),
    } as MenuItem;

    return (
        <Menu
            className={className}
            selectable={false}
            mode={menuMode}
            items={[languageMenuItemWithClass]}
        />
    );
}
