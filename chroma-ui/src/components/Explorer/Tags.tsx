// @ts-nocheck
import React, { useState, useEffect } from 'react';
import {
  Button,
  useTheme,
  Text,
  Textarea,
  Box,
  Spinner
} from '@chakra-ui/react'
import TagButton from './TagButton';
import { useAppendTagByNameToDatapointsMutation, useRemoveTagFromDatapointsMutation } from '../../graphql/graphql'

interface TagsProps {
  tags: string[]
  datapointId: Int
  setServerData: () => void
}

interface IOptions {
  options: []
}

const Tags: React.FC<TagsProps> = ({ tags, datapointId }) => {
  const theme = useTheme();
  const [isEditing, setIsEditing] = useState(false)
  const [isUpdating, setIsUpdating] = useState(false)
  const [originalTagString, setOriginalTagString] = useState('');
  const [tagString, setTagString] = useState('');
  const [tagsArray, setTagsArray] = React.useState<string[]>([]);

  const [addTagResult, addTag] = useAppendTagByNameToDatapointsMutation()
  const [unTagResult, unTag] = useRemoveTagFromDatapointsMutation()

  useEffect(() => {
    var tagStrings = tags.map(tag => tag.tag.name)
    setTagsArray(tagStrings)
    const allTags = tagStrings.join(", ")
    setTagString(allTags)
    setOriginalTagString(allTags)
  }, [tags]);

  const checkAndSetName = (e: React.ChangeEvent<HTMLInputElement>, name: string) => {
    setTagString(e.currentTarget.value)
  }

  const onSubmitName = (e: React.FormEvent) => {
    e.preventDefault()
    setIsEditing(false)

    let newTagsArray = tagString.split(",").map(tag => tag.trim())
    let originalTagsArray = originalTagString.split(",").map(tag => tag.trim())
    if (tagString === originalTagString) return

    // tags to remove
    let remove = originalTagsArray.filter(x => !newTagsArray.includes(x));

    // tags to add
    let add = newTagsArray.filter(x => !originalTagsArray.includes(x));

    // tags to add
    let keep = originalTagsArray.filter(x => newTagsArray.includes(x));

    add.map(tagToAdd => {
      const variables = { tagName: tagToAdd, datapointIds: [datapointId] };
      addTag(variables).then(result => {
        // console.log('result', result)
      });
    })

    remove.map(tagToRemove => {
      const variables = { tagName: tagToRemove, datapointIds: [datapointId] };
      unTag(variables).then(result => {
        // console.log('result', result)
      });
    })
    setTagsArray(newTagsArray)
  }

  const callback = (data: any) => {
    console.log('done', data)
  }

  const onKeyPress = (e: any) => {
    if (e.key === 'Enter') {
      onSubmitName(e)
    }
    // I would like to catch ESC here, but it's getting caught elsewhere first.
  }

  const handleBlur = (e: any) => {
    setIsEditing(false)
    setTagString(originalTagString)
  }

  return (
    <>
      {isEditing ?
        <form onSubmit={onSubmitName} style={{ width: "100%" }}>
          <Textarea
            borderColor={"rgba(0,0,0,0)"}
            borderRadius={1}
            borderWidth={2}
            size="sm"
            p="7px"
            onKeyPress={onKeyPress}
            value={tagString}
            autoFocus={true}
            onChange={(e: any) => checkAndSetName(e, e.target.value)}
            _hover={{ borderColor: theme.colors.ch_gray.light }}
            _focus={{ borderColor: theme.colors.ch_blue }}
            onBlur={handleBlur}
            placeholder='Untag selected' />
        </form>
        :
        <Box
          onClick={() => setIsEditing(!isEditing)}
          width="100%"
          borderColor={"rgba(0,0,0,0)"}
          borderRadius={1}
          borderWidth={2}
          p={1}
          _hover={{ borderColor: theme.colors.ch_gray.light, cursor: 'pointer' }}
        >
          {tagsArray.map((tag) => {
            return (
              <TagButton key={tag} tag={tag} />
            )
          })
          }
          {isUpdating ?
            <Spinner size='xs' color="gray.200" />
            : null}
        </Box>
      }

    </>
  )
}

export default Tags
