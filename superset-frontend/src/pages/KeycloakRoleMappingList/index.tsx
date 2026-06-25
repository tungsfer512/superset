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
import { useCallback, useEffect, useMemo, useState } from 'react';
import rison from 'rison';
import { t, SupersetClient } from '@superset-ui/core';
import { useListViewResource } from 'src/views/CRUD/hooks';
import withToasts from 'src/components/MessageToasts/withToasts';
import SubMenu, { SubMenuProps } from 'src/features/home/SubMenu';
import {
  FormModal,
  FormItem,
  Input,
  Select,
  Icons,
} from '@superset-ui/core/components';
import { ModalTitleWithIcon } from 'src/components/ModalTitleWithIcon';
import {
  ListView,
  ListViewFilterOperator as FilterOperator,
  ListViewActionsBar,
  type ListViewActionProps,
  type ListViewFilters,
} from 'src/components';

const RESOURCE = 'keycloak_role_mapping';

type RoleOption = { value: number; label: string };

type MappingObject = {
  id: number;
  keycloak_role: string;
  superset_role?: { id: number; name: string };
};

interface Props {
  addDangerToast: (msg: string) => void;
  addSuccessToast: (msg: string) => void;
}

interface MappingModalProps {
  show: boolean;
  onHide: () => void;
  onSave: () => void;
  mapping?: MappingObject | null;
  roleOptions: RoleOption[];
  addDangerToast: (msg: string) => void;
  addSuccessToast: (msg: string) => void;
}

function MappingModal({
  show,
  onHide,
  onSave,
  mapping,
  roleOptions,
  addDangerToast,
  addSuccessToast,
}: MappingModalProps) {
  const isEdit = Boolean(mapping);

  const handleFormSubmit = async (values: {
    keycloak_role: string;
    superset_role: number;
  }) => {
    const payload = {
      keycloak_role: values.keycloak_role,
      superset_role: values.superset_role,
    };
    try {
      if (isEdit && mapping) {
        await SupersetClient.put({
          endpoint: `/api/v1/${RESOURCE}/${mapping.id}`,
          jsonPayload: payload,
        });
        addSuccessToast(t('Role mapping updated.'));
      } else {
        await SupersetClient.post({
          endpoint: `/api/v1/${RESOURCE}/`,
          jsonPayload: payload,
        });
        addSuccessToast(t('Role mapping created.'));
      }
    } catch (err) {
      addDangerToast(t('There was an issue saving the role mapping.'));
      throw err;
    }
  };

  const initialValues = isEdit
    ? {
        keycloak_role: mapping?.keycloak_role,
        superset_role: mapping?.superset_role?.id,
      }
    : {};

  return (
    <FormModal
      show={show}
      onHide={onHide}
      name={isEdit ? 'edit-role-mapping' : 'add-role-mapping'}
      title={
        <ModalTitleWithIcon
          title={isEdit ? t('Edit role mapping') : t('Add role mapping')}
          icon={isEdit ? <Icons.EditOutlined /> : <Icons.PlusOutlined />}
        />
      }
      onSave={onSave}
      formSubmitHandler={handleFormSubmit}
      requiredFields={['keycloak_role', 'superset_role']}
      initialValues={initialValues}
    >
      <>
        <FormItem
          name="keycloak_role"
          label={t('Keycloak role')}
          rules={[{ required: true, message: t('Keycloak role is required') }]}
        >
          <Input placeholder={t('e.g. superset_admin')} />
        </FormItem>
        <FormItem
          name="superset_role"
          label={t('Superset role')}
          rules={[{ required: true, message: t('Superset role is required') }]}
        >
          <Select
            ariaLabel={t('Superset role')}
            placeholder={t('Select a Superset role')}
            options={roleOptions}
            getPopupContainer={trigger =>
              trigger.closest('.ant-modal-content') as HTMLElement
            }
          />
        </FormItem>
      </>
    </FormModal>
  );
}

function KeycloakRoleMappingList({ addDangerToast, addSuccessToast }: Props) {
  const {
    state: {
      loading,
      resourceCount: mappingCount,
      resourceCollection: mappings,
    },
    fetchData,
    refreshData,
  } = useListViewResource<MappingObject>(RESOURCE, t('role mapping'), addDangerToast);

  const [roleOptions, setRoleOptions] = useState<RoleOption[]>([]);
  const [showModal, setShowModal] = useState(false);
  const [currentMapping, setCurrentMapping] = useState<MappingObject | null>(
    null,
  );

  useEffect(() => {
    const q = rison.encode({ page: 0, page_size: 100 });
    SupersetClient.get({
      endpoint: `/api/v1/${RESOURCE}/related/superset_role?q=${q}`,
    })
      .then(({ json }) => {
        setRoleOptions(
          (json?.result || []).map((r: any) => ({
            value: r.value,
            label: r.text,
          })),
        );
      })
      .catch(() => addDangerToast(t('Could not load Superset roles')));
  }, [addDangerToast]);

  const openAdd = () => {
    setCurrentMapping(null);
    setShowModal(true);
  };
  const openEdit = (mapping: MappingObject) => {
    setCurrentMapping(mapping);
    setShowModal(true);
  };

  const handleDelete = useCallback(
    async (mapping: MappingObject) => {
      try {
        await SupersetClient.delete({
          endpoint: `/api/v1/${RESOURCE}/${mapping.id}`,
        });
        refreshData();
        addSuccessToast(t('Deleted role mapping'));
      } catch (err) {
        addDangerToast(t('There was an issue deleting the role mapping.'));
      }
    },
    [addDangerToast, addSuccessToast, refreshData],
  );

  const columns = useMemo(
    () => [
      {
        accessor: 'keycloak_role',
        id: 'keycloak_role',
        Header: t('Keycloak role'),
        Cell: ({ row: { original } }: any) => <span>{original.keycloak_role}</span>,
      },
      {
        accessor: 'superset_role.name',
        id: 'superset_role',
        Header: t('Superset role'),
        Cell: ({ row: { original } }: any) => (
          <span>{original.superset_role?.name}</span>
        ),
      },
      {
        Cell: ({ row: { original } }: any) => {
          const actions = [
            {
              label: 'edit-action',
              tooltip: t('Edit'),
              placement: 'bottom',
              icon: 'EditOutlined',
              onClick: () => openEdit(original),
            },
            {
              label: 'delete-action',
              tooltip: t('Delete'),
              placement: 'bottom',
              icon: 'DeleteOutlined',
              onClick: () => handleDelete(original),
            },
          ] as ListViewActionProps[];
          return <ListViewActionsBar actions={actions} />;
        },
        Header: t('Actions'),
        id: 'actions',
        hidden: false,
        disableSortBy: true,
        size: 'sm',
      },
    ],
    [handleDelete],
  );

  const filters: ListViewFilters = useMemo(
    () => [
      {
        Header: t('Keycloak role'),
        key: 'keycloak_role',
        id: 'keycloak_role',
        input: 'search',
        operator: FilterOperator.Contains,
      },
    ],
    [],
  );

  const subMenuButtons: SubMenuProps['buttons'] = [
    {
      name: (
        <>
          <Icons.PlusOutlined iconSize="m" /> {t('Role mapping')}
        </>
      ),
      buttonStyle: 'primary',
      onClick: openAdd,
    },
  ];

  return (
    <>
      <SubMenu name={t('Keycloak Role Mapping')} buttons={subMenuButtons} />
      <MappingModal
        show={showModal}
        onHide={() => setShowModal(false)}
        onSave={() => {
          refreshData();
          setShowModal(false);
        }}
        mapping={currentMapping}
        roleOptions={roleOptions}
        addDangerToast={addDangerToast}
        addSuccessToast={addSuccessToast}
      />
      <ListView<MappingObject>
        className="keycloak-role-mapping-list-view"
        columns={columns}
        count={mappingCount}
        data={mappings}
        fetchData={fetchData}
        refreshData={refreshData}
        filters={filters}
        initialSort={[{ id: 'keycloak_role', desc: false }]}
        loading={loading}
        pageSize={25}
        addDangerToast={addDangerToast}
        addSuccessToast={addSuccessToast}
        emptyState={{
          title: t('No role mappings yet'),
          buttonText: (
            <>
              <Icons.PlusOutlined iconSize="m" /> {t('Role mapping')}
            </>
          ),
          buttonAction: openAdd,
        }}
      />
    </>
  );
}

export default withToasts(KeycloakRoleMappingList);
